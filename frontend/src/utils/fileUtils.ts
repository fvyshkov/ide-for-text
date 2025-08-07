/**
 * Native directory picker utilities
 * Uses File System Access API when available, with fallback to manual input
 */

export interface DirectoryPickerOptions {
  mode?: 'read' | 'readwrite';
}

/**
 * Check if File System Access API is supported
 */
export const isFileSystemAccessSupported = (): boolean => {
  return 'showDirectoryPicker' in window;
};

/**
 * Open directory using file input (webkitdirectory)
 * More compatible and doesn't require full paths
 */
export const pickDirectoryWithInput = (): Promise<string | null> => {
  return new Promise((resolve) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.webkitdirectory = true;
    input.multiple = true;
    
    input.onchange = (event) => {
      const files = (event.target as HTMLInputElement).files;
      if (files && files.length > 0) {
        // Get the directory path from the first file
        const firstFile = files[0];
        const relativePath = firstFile.webkitRelativePath;
        const directoryName = relativePath.split('/')[0];
        
        // Store files for potential use
        (window as any).selectedFiles = files;
        
        resolve(directoryName);
      } else {
        resolve(null);
      }
    };
    
    input.oncancel = () => {
      resolve(null);
    };
    
    // Trigger the file picker
    input.click();
  });
};

/**
 * Open native directory picker dialog
 * Falls back to prompt if not supported
 */
export const pickDirectory = async (options: DirectoryPickerOptions = {}): Promise<string | null> => {
  try {
    if (isFileSystemAccessSupported()) {
      // Use modern File System Access API
      const directoryHandle = await (window as any).showDirectoryPicker({
        mode: options.mode || 'read'
      });
      
      // Get the directory path
      // Note: directoryHandle.name gives only the folder name, not full path
      // For security reasons, browsers don't expose full system paths
      // We'll use the handle name and let backend handle the actual path
      return directoryHandle.name;
    } else {
      // Fallback to webkitdirectory input
      return await pickDirectoryWithInput();
    }
  } catch (error) {
    // User cancelled or error occurred
    if ((error as Error).name === 'AbortError') {
      return null; // User cancelled
    }
    
    console.warn('Directory picker failed, falling back to input:', error);
    return await pickDirectoryWithInput();
  }
};

/**
 * Fallback manual directory input
 */
const promptForDirectory = (): string | null => {
  const path = prompt(
    '📁 Enter directory path:\n\n' +
    '💡 Quick options:\n' +
    '• Test directory: ./test-directory\n' +
    '• Current directory: .\n\n' +
    '📂 Or full paths:\n' +
    '• macOS: /Users/username/Documents\n' +
    '• Windows: C:\\Users\\username\\Documents\n' +
    '• Linux: /home/username/Documents'
  );
  
  return path;
};

/**
 * Get platform-specific directory suggestions
 */
export const getDirectorySuggestions = (): string[] => {
  const platform = navigator.platform.toLowerCase();
  
  if (platform.includes('mac')) {
    return [
      '/Users/' + (process.env.USER || 'username') + '/Documents',
      '/Users/' + (process.env.USER || 'username') + '/Desktop',
      '/Users/' + (process.env.USER || 'username') + '/Downloads',
      './test-directory'
    ];
  } else if (platform.includes('win')) {
    return [
      'C:\\Users\\' + (process.env.USERNAME || 'username') + '\\Documents',
      'C:\\Users\\' + (process.env.USERNAME || 'username') + '\\Desktop',
      'C:\\Users\\' + (process.env.USERNAME || 'username') + '\\Downloads',
      '.\\test-directory'
    ];
  } else {
    // Linux and others
    return [
      '/home/' + (process.env.USER || 'username') + '/Documents',
      '/home/' + (process.env.USER || 'username') + '/Desktop',
      '/home/' + (process.env.USER || 'username') + '/Downloads',
      './test-directory'
    ];
  }
};

/**
 * Simple directory picker - just pick and use
 */
export const pickDirectorySimple = async (): Promise<string | null> => {
  // Always use the input-based picker for simplicity
  return await pickDirectoryWithInput();
};

export const openFile = async (filePath: string): Promise<void> => {
  try {
    const response = await fetch('http://localhost:8001/api/open-file', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ path: filePath }),
    });

    if (!response.ok) {
      throw new Error('Failed to open file');
    }
  } catch (error) {
    console.error('Error opening file:', error);
  }
};