// Global type declarations

declare global {
  interface HTMLInputElement {
    webkitdirectory: boolean;
    webkitRelativePath?: string;
  }
  
  interface File {
    webkitRelativePath: string;
  }
  
  interface Window {
    selectedFiles?: FileList;
  }
}

export {};