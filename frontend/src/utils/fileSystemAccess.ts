/**
 * Client-side file system access utilities using File System Access API
 * Allows working with local directories entirely in the browser
 */

import { FileTreeItem, FileContent } from '../types';

/**
 * Recursively read directory tree from FileSystemDirectoryHandle
 */
export async function readDirectoryTree(
  dirHandle: any,
  parentPath: string = ''
): Promise<FileTreeItem[]> {
  const items: FileTreeItem[] = [];

  // @ts-ignore - File System Access API types
  for await (const entry of dirHandle.values()) {
    const itemPath = parentPath ? `${parentPath}/${entry.name}` : entry.name;

    if (entry.kind === 'directory') {
      const subDirHandle = entry;
      const children = await readDirectoryTree(subDirHandle, itemPath);
      items.push({
        name: entry.name,
        path: itemPath,
        is_directory: true,
        children: children
      });
    } else {
      items.push({
        name: entry.name,
        path: itemPath,
        is_directory: false,
        children: null
      });
    }
  }

  // Sort: directories first, then files, alphabetically
  return items.sort((a, b) => {
    if (a.is_directory && !b.is_directory) return -1;
    if (!a.is_directory && b.is_directory) return 1;
    return a.name.localeCompare(b.name);
  });
}

/**
 * Read file content from a path within the directory handle
 */
export async function readFileFromHandle(
  rootHandle: any,
  filePath: string
): Promise<FileContent> {
  const pathParts = filePath.split('/').filter(p => p);

  // Navigate to the file
  let currentHandle: any = rootHandle;

  for (let i = 0; i < pathParts.length - 1; i++) {
    currentHandle = await currentHandle.getDirectoryHandle(pathParts[i]);
  }

  const fileName = pathParts[pathParts.length - 1];
  const fileHandle = await currentHandle.getFileHandle(fileName);
  const file = await fileHandle.getFile();

  // Check if file is binary (simple heuristic)
  const isBinary = !file.type.startsWith('text/') &&
                   !file.type.includes('json') &&
                   !file.type.includes('javascript') &&
                   !file.name.match(/\.(txt|md|js|ts|tsx|jsx|py|java|cpp|c|h|css|html|xml|yaml|yml|json|csv)$/i);

  if (isBinary) {
    return {
      path: filePath,
      content: '',
      is_binary: true,
      file_type: file.type.startsWith('image/') ? 'image' : undefined
    };
  }

  const content = await file.text();

  return {
    path: filePath,
    content,
    is_binary: false
  };
}

/**
 * Write content to a file within the directory handle
 */
export async function writeFileToHandle(
  rootHandle: any,
  filePath: string,
  content: string
): Promise<void> {
  const pathParts = filePath.split('/').filter(p => p);

  // Navigate to the parent directory, creating directories as needed
  let currentHandle: any = rootHandle;

  for (let i = 0; i < pathParts.length - 1; i++) {
    currentHandle = await currentHandle.getDirectoryHandle(pathParts[i], { create: true });
  }

  const fileName = pathParts[pathParts.length - 1];
  const fileHandle = await currentHandle.getFileHandle(fileName, { create: true });

  const writable = await fileHandle.createWritable();
  await writable.write(content);
  await writable.close();
}

/**
 * Check if File System Access API is supported
 */
export function isFileSystemAccessSupported(): boolean {
  return typeof window !== 'undefined' && 'showDirectoryPicker' in window;
}

/**
 * Store to keep track of the current directory handle
 */
class FileSystemStore {
  private rootHandle: any = null;
  private rootPath: string = '';

  setRoot(handle: any, path: string) {
    this.rootHandle = handle;
    this.rootPath = path;
  }

  getRoot(): any {
    return this.rootHandle;
  }

  getRootPath(): string {
    return this.rootPath;
  }

  clear() {
    this.rootHandle = null;
    this.rootPath = '';
  }
}

export const fileSystemStore = new FileSystemStore();