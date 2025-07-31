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
      
      // Offer user better options for path handling
      const userChoice = window.confirm(
        `✅ Folder selected: "${folderName}"\n\n` +
        '🎯 Choose how to proceed:\n\n' +
        'OK = Enter full absolute path manually\n' +
        'Cancel = Use relative path (./' + folderName + ')\n\n' +
        '💡 Tip: Relative path works if the folder is in your current directory'
      );
      
      if (userChoice) {
        // User wants to enter full path manually
        const fullPath = prompt(
          `Enter the full path to "${folderName}":\n\n` +
          'Examples:\n' +
          `• macOS: /Users/username/path/to/${folderName}\n` +
          `• Windows: C:\\Users\\username\\path\\to\\${folderName}\n` +
          `• Linux: /home/username/path/to/${folderName}`
        );
        return fullPath;
      } else {
        // Use relative path
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