import {expect, test} from '@playwright/test';
import path from 'path';

test('accessible labels, landmarks, and status messaging', async ({page}) => {
  await page.goto('/');
  await expect(page.getByRole('heading', {level: 1, name: 'Form 8825 Review'})).toBeVisible();
  await expect(page.getByLabel('Upload Form 8825 PDF')).toBeVisible();

  await page.getByLabel('Upload Form 8825 PDF').setInputFiles(path.resolve('../data/f8825_multi_ABC.pdf'));
  const section = page.getByTestId('property-A');
  await expect(section.getByRole('heading', {level: 2, name: 'Property A'})).toBeVisible();
  await expect(page.getByLabel('A-gross_rents')).toBeVisible();
  await expect(section.getByRole('button', {name: 'View change history'})).toBeVisible();

  const unlabeled = await page.locator('input').evaluateAll((nodes) => nodes.filter((node) => {
    if (node.getAttribute('aria-label')) return false;
    if (node.id && document.querySelector(`label[for="${node.id}"]`)) return false;
    return !node.closest('label');
  }).length);
  expect(unlabeled).toBe(0);
});

test('validation errors are announced as alerts', async ({page}) => {
  await page.goto('/');
  await page.getByLabel('Upload Form 8825 PDF').setInputFiles({
    name: 'bad.pdf', mimeType: 'application/pdf', buffer: Buffer.from('bad'),
  });
  await expect(page.getByRole('alert')).toContainText('File is not a PDF');
});
