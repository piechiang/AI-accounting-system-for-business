#!/usr/bin/env python3
"""
Classification Pipeline Evaluation Script

Evaluates the performance of the classification pipeline across different modes:
- Rule-based classification
- Embedding-based classification  
- ML-based classification
- LLM-based classification
- Auto mode (full pipeline)

Generates accuracy metrics, confusion matrices, and performance reports.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.database import get_db
from app.services.classification_service import ClassificationService
from app.models.transactions import TransactionClean
from app.models.accounts import ChartOfAccounts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClassificationEvaluator:
    """Evaluates classification pipeline performance"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.classification_service = ClassificationService(db_session)
        self.results = {}
        self.test_data = []
        
    async def load_test_data(self, limit: int = 200) -> List[Dict[str, Any]]:
        """
        Load test transactions for evaluation.
        
        Args:
            limit: Maximum number of transactions to load
            
        Returns:
            List of test transactions with ground truth labels
        """
        logger.info(f"Loading test data (limit: {limit})")
        
        # Get transactions that have been reviewed (ground truth)
        reviewed_transactions = self.db.query(TransactionClean).filter(
            TransactionClean.is_reviewed == "true",
            TransactionClean.coa_id.isnot(None)
        ).limit(limit).all()
        
        test_data = []
        for txn in reviewed_transactions:
            coa = self.db.query(ChartOfAccounts).filter(
                ChartOfAccounts.id == txn.coa_id
            ).first()
            
            test_data.append({
                'transaction_id': txn.id,
                'description': txn.description_normalized or "",
                'counterparty': txn.counterparty_normalized or "",
                'amount': float(txn.amount_base) if txn.amount_base else 0.0,
                'date': txn.transaction_date.isoformat() if txn.transaction_date else None,
                'ground_truth_coa_id': txn.coa_id,
                'ground_truth_coa_name': coa.name if coa else "Unknown",
                'ground_truth_coa_code': coa.code if coa else "Unknown"
            })
        
        self.test_data = test_data
        logger.info(f"Loaded {len(test_data)} test transactions")
        return test_data
    
    async def evaluate_mode(self, mode: str) -> Dict[str, Any]:
        """
        Evaluate classification performance for a specific mode.
        
        Args:
            mode: Classification mode ('rule', 'embed', 'ml', 'llm', 'auto')
            
        Returns:
            Evaluation metrics
        """
        logger.info(f"Evaluating mode: {mode}")
        
        if not self.test_data:
            raise ValueError("No test data loaded. Call load_test_data() first.")
        
        predictions = []
        ground_truth = []
        processing_times = []
        confidence_scores = []
        
        for i, test_txn in enumerate(self.test_data):
            if i % 50 == 0:
                logger.info(f"Processing transaction {i+1}/{len(self.test_data)}")
            
            start_time = time.time()
            
            # Temporarily clear the transaction's classification to get fresh prediction
            txn = self.db.query(TransactionClean).filter(
                TransactionClean.id == test_txn['transaction_id']
            ).first()
            
            if txn:
                original_coa_id = txn.coa_id
                original_confidence = txn.confidence_score
                
                # Clear classification
                txn.coa_id = None
                txn.confidence_score = None
                self.db.commit()
                
                try:
                    # Get prediction
                    result = await self.classification_service.classify_transactions_pipeline(
                        transaction_ids=[test_txn['transaction_id']],
                        force_reclassify=True,
                        mode=mode
                    )
                    
                    processing_time = time.time() - start_time
                    processing_times.append(processing_time)
                    
                    if result and len(result) > 0:
                        pred = result[0]
                        predicted_coa_id = pred.get('predicted_coa_id')
                        confidence = pred.get('confidence_score', 0.0)
                        
                        predictions.append(predicted_coa_id)
                        confidence_scores.append(confidence)
                    else:
                        predictions.append(None)
                        confidence_scores.append(0.0)
                    
                    ground_truth.append(test_txn['ground_truth_coa_id'])
                    
                finally:
                    # Restore original classification
                    txn.coa_id = original_coa_id
                    txn.confidence_score = original_confidence
                    self.db.commit()
        
        # Calculate metrics
        metrics = self._calculate_metrics(
            ground_truth, predictions, confidence_scores, processing_times, mode
        )
        
        return metrics
    
    def _calculate_metrics(
        self, 
        ground_truth: List[int], 
        predictions: List[Optional[int]], 
        confidence_scores: List[float],
        processing_times: List[float],
        mode: str
    ) -> Dict[str, Any]:
        """Calculate evaluation metrics"""
        
        # Handle None predictions
        valid_indices = [i for i, pred in enumerate(predictions) if pred is not None]
        valid_ground_truth = [ground_truth[i] for i in valid_indices]
        valid_predictions = [predictions[i] for i in valid_indices]
        valid_confidences = [confidence_scores[i] for i in valid_indices]
        
        coverage = len(valid_indices) / len(predictions) if predictions else 0
        
        metrics = {
            'mode': mode,
            'total_samples': len(predictions),
            'predictions_made': len(valid_indices),
            'coverage': coverage,
            'avg_processing_time': np.mean(processing_times) if processing_times else 0,
            'avg_confidence': np.mean(valid_confidences) if valid_confidences else 0
        }
        
        if valid_ground_truth and valid_predictions:
            # Accuracy
            accuracy = accuracy_score(valid_ground_truth, valid_predictions)
            metrics['accuracy'] = accuracy
            
            # Get unique labels for classification report
            unique_labels = sorted(set(valid_ground_truth + valid_predictions))
            
            # Classification report
            class_report = classification_report(
                valid_ground_truth, 
                valid_predictions,
                labels=unique_labels,
                output_dict=True,
                zero_division=0
            )
            metrics['classification_report'] = class_report
            
            # Confusion matrix
            cm = confusion_matrix(valid_ground_truth, valid_predictions, labels=unique_labels)
            metrics['confusion_matrix'] = cm.tolist()
            metrics['confusion_matrix_labels'] = unique_labels
            
            # Confidence-based metrics
            if valid_confidences:
                high_conf_indices = [i for i, conf in enumerate(valid_confidences) if conf >= 0.8]
                if high_conf_indices:
                    high_conf_ground_truth = [valid_ground_truth[i] for i in high_conf_indices]
                    high_conf_predictions = [valid_predictions[i] for i in high_conf_indices]
                    high_conf_accuracy = accuracy_score(high_conf_ground_truth, high_conf_predictions)
                    metrics['high_confidence_accuracy'] = high_conf_accuracy
                    metrics['high_confidence_samples'] = len(high_conf_indices)
        else:
            metrics['accuracy'] = 0.0
            metrics['classification_report'] = {}
            metrics['confusion_matrix'] = []
            metrics['confusion_matrix_labels'] = []
        
        return metrics
    
    async def run_full_evaluation(self) -> Dict[str, Any]:
        """Run evaluation across all modes"""
        logger.info("Starting full evaluation")
        
        modes = ['rule', 'embed', 'ml', 'llm', 'auto']
        results = {}
        
        for mode in modes:
            logger.info(f"Evaluating mode: {mode}")
            try:
                mode_results = await self.evaluate_mode(mode)
                results[mode] = mode_results
            except Exception as e:
                logger.error(f"Error evaluating mode {mode}: {e}")
                results[mode] = {'error': str(e)}
        
        # Add summary statistics
        results['summary'] = self._generate_summary(results)
        results['timestamp'] = datetime.now().isoformat()
        
        self.results = results
        return results
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics across all modes"""
        summary = {
            'best_accuracy_mode': None,
            'best_accuracy_score': 0.0,
            'best_coverage_mode': None,
            'best_coverage_score': 0.0,
            'fastest_mode': None,
            'fastest_time': float('inf'),
            'mode_comparison': {}
        }
        
        for mode, metrics in results.items():
            if mode == 'summary' or 'error' in metrics:
                continue
            
            accuracy = metrics.get('accuracy', 0.0)
            coverage = metrics.get('coverage', 0.0)
            avg_time = metrics.get('avg_processing_time', float('inf'))
            
            # Track best performers
            if accuracy > summary['best_accuracy_score']:
                summary['best_accuracy_score'] = accuracy
                summary['best_accuracy_mode'] = mode
            
            if coverage > summary['best_coverage_score']:
                summary['best_coverage_score'] = coverage
                summary['best_coverage_mode'] = mode
            
            if avg_time < summary['fastest_time']:
                summary['fastest_time'] = avg_time
                summary['fastest_mode'] = mode
            
            # Store for comparison
            summary['mode_comparison'][mode] = {
                'accuracy': accuracy,
                'coverage': coverage,
                'avg_time': avg_time,
                'avg_confidence': metrics.get('avg_confidence', 0.0)
            }
        
        return summary
    
    def save_results(self, output_path: str = "classification_evaluation_results.json"):
        """Save evaluation results to JSON file"""
        if not self.results:
            raise ValueError("No results to save. Run evaluation first.")
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"Results saved to {output_file}")
    
    def generate_plots(self, output_dir: str = "evaluation_plots"):
        """Generate visualization plots"""
        if not self.results:
            raise ValueError("No results to plot. Run evaluation first.")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Accuracy comparison plot
        self._plot_accuracy_comparison(output_path)
        
        # Coverage vs Accuracy plot
        self._plot_coverage_vs_accuracy(output_path)
        
        # Processing time comparison
        self._plot_processing_times(output_path)
        
        # Confusion matrices
        self._plot_confusion_matrices(output_path)
        
        logger.info(f"Plots saved to {output_path}")
    
    def _plot_accuracy_comparison(self, output_path: Path):
        """Plot accuracy comparison across modes"""
        modes = []
        accuracies = []
        coverages = []
        
        for mode, metrics in self.results.items():
            if mode == 'summary' or 'error' in metrics:
                continue
            modes.append(mode)
            accuracies.append(metrics.get('accuracy', 0.0))
            coverages.append(metrics.get('coverage', 0.0))
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Accuracy plot
        bars1 = ax1.bar(modes, accuracies, color='skyblue', alpha=0.7)
        ax1.set_title('Classification Accuracy by Mode')
        ax1.set_ylabel('Accuracy')
        ax1.set_ylim(0, 1)
        
        # Add value labels on bars
        for bar, acc in zip(bars1, accuracies):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'{acc:.3f}', ha='center', va='bottom')
        
        # Coverage plot
        bars2 = ax2.bar(modes, coverages, color='lightgreen', alpha=0.7)
        ax2.set_title('Classification Coverage by Mode')
        ax2.set_ylabel('Coverage')
        ax2.set_ylim(0, 1)
        
        # Add value labels on bars
        for bar, cov in zip(bars2, coverages):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'{cov:.3f}', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(output_path / 'accuracy_coverage_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_coverage_vs_accuracy(self, output_path: Path):
        """Plot coverage vs accuracy scatter plot"""
        modes = []
        accuracies = []
        coverages = []
        
        for mode, metrics in self.results.items():
            if mode == 'summary' or 'error' in metrics:
                continue
            modes.append(mode)
            accuracies.append(metrics.get('accuracy', 0.0))
            coverages.append(metrics.get('coverage', 0.0))
        
        plt.figure(figsize=(10, 8))
        scatter = plt.scatter(coverages, accuracies, s=100, alpha=0.7, c=range(len(modes)), cmap='viridis')
        
        for i, mode in enumerate(modes):
            plt.annotate(mode, (coverages[i], accuracies[i]), 
                        xytext=(5, 5), textcoords='offset points')
        
        plt.xlabel('Coverage')
        plt.ylabel('Accuracy')
        plt.title('Coverage vs Accuracy by Classification Mode')
        plt.grid(True, alpha=0.3)
        plt.xlim(0, 1.1)
        plt.ylim(0, 1.1)
        
        plt.savefig(output_path / 'coverage_vs_accuracy.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_processing_times(self, output_path: Path):
        """Plot processing time comparison"""
        modes = []
        times = []
        
        for mode, metrics in self.results.items():
            if mode == 'summary' or 'error' in metrics:
                continue
            modes.append(mode)
            times.append(metrics.get('avg_processing_time', 0.0))
        
        plt.figure(figsize=(10, 6))
        bars = plt.bar(modes, times, color='orange', alpha=0.7)
        plt.title('Average Processing Time by Mode')
        plt.ylabel('Time (seconds)')
        
        # Add value labels on bars
        for bar, time_val in zip(bars, times):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.001,
                    f'{time_val:.3f}s', ha='center', va='bottom')
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_path / 'processing_times.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_confusion_matrices(self, output_path: Path):
        """Plot confusion matrices for each mode"""
        for mode, metrics in self.results.items():
            if mode == 'summary' or 'error' in metrics:
                continue
            
            cm = metrics.get('confusion_matrix')
            labels = metrics.get('confusion_matrix_labels')
            
            if cm and labels:
                plt.figure(figsize=(10, 8))
                sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                           xticklabels=labels, yticklabels=labels)
                plt.title(f'Confusion Matrix - {mode.upper()} Mode')
                plt.ylabel('True Label')
                plt.xlabel('Predicted Label')
                plt.tight_layout()
                plt.savefig(output_path / f'confusion_matrix_{mode}.png', 
                           dpi=300, bbox_inches='tight')
                plt.close()
    
    def print_summary(self):
        """Print evaluation summary to console"""
        if not self.results:
            print("No results to display. Run evaluation first.")
            return
        
        print("\n" + "="*80)
        print("CLASSIFICATION PIPELINE EVALUATION SUMMARY")
        print("="*80)
        
        summary = self.results.get('summary', {})
        
        print(f"\nBest Accuracy: {summary.get('best_accuracy_score', 0):.3f} ({summary.get('best_accuracy_mode', 'N/A')})")
        print(f"Best Coverage: {summary.get('best_coverage_score', 0):.3f} ({summary.get('best_coverage_mode', 'N/A')})")
        print(f"Fastest Mode: {summary.get('fastest_time', 0):.3f}s ({summary.get('fastest_mode', 'N/A')})")
        
        print("\nDetailed Results by Mode:")
        print("-" * 60)
        print(f"{'Mode':<10} {'Accuracy':<10} {'Coverage':<10} {'Avg Time':<12} {'Avg Conf':<10}")
        print("-" * 60)
        
        comparison = summary.get('mode_comparison', {})
        for mode, stats in comparison.items():
            print(f"{mode:<10} {stats['accuracy']:<10.3f} {stats['coverage']:<10.3f} "
                  f"{stats['avg_time']:<12.3f} {stats['avg_confidence']:<10.3f}")
        
        print("-" * 60)

async def main():
    """Main evaluation function"""
    parser = argparse.ArgumentParser(description="Evaluate classification pipeline")
    parser.add_argument("--limit", type=int, default=200, help="Number of test samples")
    parser.add_argument("--output-dir", default="evaluation_results", help="Output directory")
    parser.add_argument("--no-plots", action="store_true", help="Skip generating plots")
    args = parser.parse_args()
    
    # Setup database
    db_session = next(get_db())
    
    try:
        evaluator = ClassificationEvaluator(db_session)
        
        # Load test data
        await evaluator.load_test_data(limit=args.limit)
        
        # Run evaluation
        results = await evaluator.run_full_evaluation()
        
        # Create output directory
        output_path = Path(args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save results
        evaluator.save_results(output_path / "results.json")
        
        # Generate plots
        if not args.no_plots:
            try:
                evaluator.generate_plots(output_path / "plots")
            except ImportError as e:
                logger.warning(f"Could not generate plots: {e}")
        
        # Print summary
        evaluator.print_summary()
        
        logger.info(f"Evaluation complete. Results saved to {output_path}")
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise
    finally:
        db_session.close()

if __name__ == "__main__":
    import argparse
    asyncio.run(main())