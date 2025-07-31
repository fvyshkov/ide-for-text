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
      // Fallback to manual input
      return promptForDirectory();
    }
  } catch (error) {
    // User cancelled or error occurred
    if ((error as Error).name === 'AbortError') {
      return null; // User cancelled
    }
    
    console.warn('Directory picker failed, falling back to manual input:', error);
    return promptForDirectory();
  }
};

/**
 * Fallback manual directory input
 */
const promptForDirectory = (): string | null => {
  const path = prompt(
    'Enter directory path:\n\n' +
    'Examples:\n' +
    '• macOS: /Users/username/Documents\n' +
    '• Windows: C:\\Users\\username\\Documents\n' +
    '• Linux: /home/username/Documents\n' +
    '• Current project: ./test-directory'
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
 * Enhanced directory picker with better UX
 */
export const pickDirectoryEnhanced = async (): Promise<string | null> => {
  try {
    if (isFileSystemAccessSupported()) {
      // Try native picker first
      const directoryHandle = await (window as any).showDirectoryPicker({
        mode: 'read'
      });
      
      // For File System Access API, we need to work with the handle
      // Since we can't get the full path, we'll pass the handle name
      // and let the user know this is a browser limitation
      
      const folderName = directoryHandle.name;
      
      // We could also try to resolve relative path, but for now
      // let's use a different approach - ask user to confirm or enter full path
      const shouldUseFullPath = confirm(
        `Selected folder: "${folderName}"\n\n` +
        'Due to browser security restrictions, we need the full path.\n' +
        'Click OK to enter the full path manually, or Cancel to use current directory.'
      );
      
      if (shouldUseFullPath) {
        return promptForDirectory();
      } else {
        // Use current directory + folder name as fallback
        return `./${folderName}`;
      }
    } else {
      return promptForDirectory();
    }
  } catch (error) {
    if ((error as Error).name === 'AbortError') {
      return null;
    }
    return promptForDirectory();
  }
};