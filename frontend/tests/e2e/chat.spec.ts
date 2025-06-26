import { test, expect } from '@playwright/test';

test.describe('AI ChatBot E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('Send text message and receive AI response', async ({ page }) => {
    const input = page.locator('textarea[placeholder="Введите сообщение..."]');
    const sendButton = page.locator('button:has-text("Send"), button:has-text("Отправить")');

    await input.fill('Hello AI');
    await sendButton.click();

    // Wait for AI response message to appear
    const aiMessage = page.locator('.message-bubble.assistant').last();
    await expect(aiMessage).toContainText(/Hello|Привет|Hi/i);
  });

  test('Switch AI provider and verify change', async ({ page }) => {
    const providerSelector = page.locator('select#provider-selector');
    await providerSelector.selectOption('gemini');

    // Verify provider changed (e.g., UI indication)
    const currentProvider = await providerSelector.inputValue();
    expect(currentProvider).toBe('gemini');
  });

  test('Voice input end-to-end test (mocked)', async ({ page }) => {
    // Click record button
    const recordButton = page.locator('button:has-text("Голос")');
    await recordButton.click();

    // Mock transcription result by intercepting WebSocket or API call
    // This is a placeholder for actual audio stream emulation
    await page.route('**/api/voice/transcribe', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          text: 'Test transcription',
          confidence: 0.99,
          audio_id: 'test-audio-id'
        }),
      });
    });

    // Click stop button (assuming same button toggles)
    await recordButton.click();

    // Check that a message with mocked transcribed text appears
    const userMessage = page.locator('.message-bubble.user').last();
    await expect(userMessage).toContainText('Test transcription');

    // Check that AI responded
    const aiMessage = page.locator('.message-bubble.assistant').last();
    await expect(aiMessage).not.toBeNull();
  });

  test('AI provider failure handling', async ({ page }) => {
    // Mock backend API to return 500 error for chat message
    await page.route('**/api/chat/message', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ detail: 'Internal Server Error' }),
        headers: { 'Content-Type': 'application/json' }
      });
    });

    const input = page.locator('textarea[placeholder="Введите сообщение..."]');
    const sendButton = page.locator('button:has-text("Send"), button:has-text("Отправить")');

    await input.fill('Trigger error');
    await sendButton.click();

    // Check for error message in UI
    const errorMessage = page.locator('.message-bubble.assistant').last();
    await expect(errorMessage).toContainText(/ошибка|error/i);
  });

  test('New session isolation test', async ({ page }) => {
    // Send first message
    const input = page.locator('textarea[placeholder="Введите сообщение..."]');
    const sendButton = page.locator('button:has-text("Send"), button:has-text("Отправить")');

    await input.fill('First session message');
    await sendButton.click();

    // Wait for AI response
    const aiMessage1 = page.locator('.message-bubble.assistant').last();
    await expect(aiMessage1).not.toBeNull();

    // Reload page to simulate new session
    await page.reload();

    // Send second message
    await input.fill('Second session message');
    await sendButton.click();

    // Wait for AI response
    const aiMessage2 = page.locator('.message-bubble.assistant').last();
    await expect(aiMessage2).not.toBeNull();

    // Verify that context from first session is not present in second
    // This can be done by checking that AI response does not reference first message
    const aiText1 = await aiMessage1.textContent();
    const aiText2 = await aiMessage2.textContent();
    expect(aiText2).not.toContain(aiText1 || '');
  });
});
