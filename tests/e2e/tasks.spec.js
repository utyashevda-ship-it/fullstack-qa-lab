const { test, expect } = require('@playwright/test');
const { randomUUID } = require('node:crypto');

// Every test owns its data: no global reset endpoint or shared fixed title.
test('UI lifecycle persists after reload', async ({ page, request }) => {
  const title = `UI ${randomUUID()}`;
  let id;
  try {
    await page.goto('/');
    await page.getByLabel('Task title', { exact: true }).fill(title);
    await page.getByRole('button', { name: 'Add task' }).click();
    const row = page.getByTestId('task').filter({ hasText: title });
    await expect(row).toBeVisible();
    id = (await (await request.get('/api/tasks')).json()).find(t => t.title === title).id;
    await row.getByRole('checkbox').check();
    await expect(row.getByRole('checkbox')).toBeChecked();
    await page.reload();
    await expect(row.getByRole('checkbox')).toBeChecked();
    await row.getByRole('button', { name: 'Delete' }).click();
    await expect(row).toHaveCount(0);
  } finally { if (id) await request.delete(`/api/tasks/${id}`); }
});

test('API-created task is rendered as text, not executable HTML', async ({ page, request }) => {
  const title = `<img src=x onerror="window.injected=true"> ${randomUUID()}`;
  const response = await request.post('/api/tasks', { data: { title } });
  expect(response.status()).toBe(201);
  const task = await response.json();
  try {
    await page.goto('/');
    const row = page.getByTestId('task').filter({ hasText: title });
    await expect(row).toBeVisible();
    await expect(row.locator('img')).toHaveCount(0);
    expect(await page.evaluate(() => window.injected)).toBeUndefined();
  } finally { await request.delete(`/api/tasks/${task.id}`); }
});

test('Playwright API lifecycle and validation', async ({ request }) => {
  expect((await request.post('/api/tasks', { data: { title: ' ' } })).status()).toBe(422);
  const response = await request.post('/api/tasks', { data: { title: `API ${randomUUID()}` } });
  expect(response.status()).toBe(201);
  const task = await response.json();
  try {
    const update = await request.patch(`/api/tasks/${task.id}`, { data: { done: true } });
    expect(update.status()).toBe(200);
    expect((await update.json()).done).toBe(true);
    expect(await (await request.get('/api/tasks')).json()).toContainEqual({ ...task, done: true });
  } finally { expect((await request.delete(`/api/tasks/${task.id}`)).status()).toBe(204); }
});
