import React from 'react';

export function Toaster() {
  return (
    <div 
      id="toast-container" 
      className="fixed top-4 right-4 z-50 space-y-2"
      aria-live="polite"
    >
      {/* Toast notifications will be inserted here */}
    </div>
  );
}

// Simple toast utility function
export const toast = {
  success: (message: string) => {
    createToast(message, 'success');
  },
  error: (message: string) => {
    createToast(message, 'error');
  },
  info: (message: string) => {
    createToast(message, 'info');
  },
};

function createToast(message: string, type: 'success' | 'error' | 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `
    p-4 rounded-lg shadow-lg max-w-sm w-full transform transition-all duration-300 ease-in-out
    ${type === 'success' ? 'bg-green-500 text-white' : ''}
    ${type === 'error' ? 'bg-red-500 text-white' : ''}
    ${type === 'info' ? 'bg-blue-500 text-white' : ''}
  `;
  
  toast.innerHTML = `
    <div class="flex items-center justify-between">
      <span>${message}</span>
      <button onclick="this.parentElement.parentElement.remove()" class="ml-2 text-white hover:text-gray-200">×</button>
    </div>
  `;

  container.appendChild(toast);

  // Auto remove after 4 seconds
  setTimeout(() => {
    if (toast.parentNode) {
      toast.remove();
    }
  }, 4000);
}