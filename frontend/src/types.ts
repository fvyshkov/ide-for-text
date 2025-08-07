export interface FileTreeItem {
  name: string;
  path: string;
  is_directory: boolean;
  children?: FileTreeItem[];
}

export interface FileContent {
  path: string;
  content: string;
  is_binary: boolean;
  file_type?: string;
}