import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import FileTree from './FileTree';
import { FileTreeItem } from '../types';

const mockItems: FileTreeItem[] = [
  {
    name: 'src',
    path: '/src',
    is_directory: true,
    children: [
      {
        name: 'App.tsx',
        path: '/src/App.tsx',
        is_directory: false,
        children: null,
      },
    ],
  },
  {
    name: 'package.json',
    path: '/package.json',
    is_directory: false,
    children: null,
  },
];

test('renders file tree and handles clicks', () => {
  const onFileSelect = jest.fn();
  render(
    <FileTree items={mockItems} onFileSelect={onFileSelect} selectedFile={null} />
  );

  // Check that the top-level items are rendered
  expect(screen.getByText('src')).toBeInTheDocument();
  expect(screen.getByText('package.json')).toBeInTheDocument();

  // The child item should not be visible initially
  expect(screen.queryByText('App.tsx')).not.toBeInTheDocument();

  // Click the directory to expand it
  fireEvent.click(screen.getByText('src'));

  // The child item should now be visible
  expect(screen.getByText('App.tsx')).toBeInTheDocument();

  // Click the file
  fireEvent.click(screen.getByText('App.tsx'));

  // The onFileSelect callback should have been called with the correct path
  expect(onFileSelect).toHaveBeenCalledWith('/src/App.tsx');
});
