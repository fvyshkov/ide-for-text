import { test, expect } from '@playwright/test';

test.describe('Text IDE Basic Functionality', () => {
  test.beforeEach(async ({ page }) => {
    // Start from the index page
    await page.goto('http://localhost:3000/');
  });

  test('should load the application and show empty state', async ({ page }) => {
    // Check main UI elements are present
    await expect(page.getByText('Text IDE')).toBeVisible();
    await expect(page.getByTitle('Open folder')).toBeVisible();
    await expect(page.getByText('No file selected')).toBeVisible();
  });

  test('should open test directory and show files', async ({ page }) => {
    // Use test mode to avoid system folder picker
    await page.request.post('http://localhost:8001/api/pick-directory', {
      data: { test_mode: true }
    });
    
    // Wait for file tree to load
    await expect(page.getByText('example.txt')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('script.js')).toBeVisible();
    
    // Verify directory structure
    await expect(page.getByText('code-samples')).toBeVisible();
    await expect(page.getByText('documents')).toBeVisible();
  });

  test('should open and display file content', async ({ page }) => {
    // Open test directory first
    await page.request.post('http://localhost:8001/api/pick-directory', {
      data: { test_mode: true }
    });
    await expect(page.getByText('example.txt')).toBeVisible({ timeout: 5000 });

    // Click on example.txt
    await page.getByText('example.txt').click();
    
    // Wait for editor to load and check content
    await expect(page.locator('.monaco-editor')).toBeVisible({ timeout: 10000 });
    
    // Wait for file content to be loaded into editor
    await page.waitForSelector('.monaco-editor .view-line', { timeout: 10000 });
    
    // Check if file path is displayed
    await expect(page.getByText('example.txt', { exact: false })).toBeVisible();
  });

  test('should edit file and save changes', async ({ page }) => {
    // Open test directory and file
    await page.request.post('http://localhost:8001/api/pick-directory', {
      data: { test_mode: true }
    });
    await expect(page.getByText('example.txt')).toBeVisible({ timeout: 5000 });
    await page.getByText('example.txt').click();
    
    // Wait for editor and its content
    const editor = page.locator('.monaco-editor');
    await expect(editor).toBeVisible({ timeout: 10000 });
    await page.waitForSelector('.monaco-editor .view-line', { timeout: 10000 });
    
    // Type some text (need to handle Monaco editor)
    await page.keyboard.type('Test content from e2e test');
    
    // Content should be automatically saved (we have auto-save)
    // Wait a bit for save to complete
    await page.waitForTimeout(1000);
    
    // Refresh the page to verify changes persist
    await page.reload();
    
    // Wait for content to load and verify it contains our text
    await expect(editor).toBeVisible();
    await expect(page.getByText('Test content from e2e test')).toBeVisible();
  });

  test('should handle binary files correctly', async ({ page }) => {
    // Open test directory
    await page.request.post('http://localhost:8001/api/pick-directory', {
      data: { test_mode: true }
    });
    await expect(page.getByText('example.txt')).toBeVisible({ timeout: 5000 });

    // Try to open a binary file (we'll use data-samples directory)
    await page.getByText('data-samples').click();
    await page.getByText('test.xlsx', { exact: false }).click();
    
    // Should show binary file message
    await expect(page.getByText('Data File')).toBeVisible();
    
    // Should show AI analysis options
    await expect(page.getByText('Show a summary of the data')).toBeVisible();
    await expect(page.getByText('Analyze specific columns')).toBeVisible();
  });

  test('should toggle theme', async ({ page }) => {
    // Get theme toggle button
    const themeButton = page.getByTitle(/Switch to (dark|light) theme/);
    
    // Get initial theme
    const initialTheme = await page.evaluate(() => document.body.className);
    
    // Click theme toggle
    await themeButton.click();
    
    // Check if theme changed
    const newTheme = await page.evaluate(() => document.body.className);
    expect(newTheme).not.toBe(initialTheme);
  });

  test('should interact with AI Assistant', async ({ page }) => {
    // Open test directory and file
    await page.request.post('http://localhost:8001/api/pick-directory', {
      data: { test_mode: true }
    });
    await expect(page.getByText('example.txt')).toBeVisible({ timeout: 5000 });
    await page.getByText('example.txt').click();
    
    // Find AI chat input
    const chatInput = page.getByPlaceholder('Ask me about your code, project, or anything else...');
    await expect(chatInput).toBeVisible();
    
    // Type a question
    await chatInput.fill('What is this file about?');
    await chatInput.press('Enter');
    
    // Wait for AI response
    await expect(page.getByText('Analyzing request', { exact: false })).toBeVisible();
    
    // Should eventually show some response
    await expect(page.locator('.message.ai')).toBeVisible({ timeout: 10000 });
  });
});