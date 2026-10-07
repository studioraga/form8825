import {expect, test} from '@playwright/test';
import path from 'path';

test('upload A/B/C, edit source value, recalculate, audit, and persist across reload', async ({page}) => {
  await page.goto('/');
  await page.getByTestId('pdf-upload').setInputFiles(path.resolve('../data/f8825_multi_ABC.pdf'));

  const a = page.getByTestId('property-A');
  await expect(a).toBeVisible();
  await expect(page.getByTestId('property-B')).toBeVisible();
  await expect(page.getByTestId('property-C')).toBeVisible();

  const grossRents = page.getByLabel('A-gross_rents');
  await expect(grossRents).toHaveValue('120000');
  await expect(page.getByTestId('A-total-income')).toHaveText('125,000');
  await expect(page.getByTestId('A-total-expense')).toHaveText('89,000');
  await expect(page.getByTestId('A-net-income')).toHaveText('36,000');

  await grossRents.fill('121000');
  await grossRents.press('Tab');

  await expect(page.getByTestId('A-total-income')).toHaveText('126,000');
  await expect(page.getByTestId('A-total-expense')).toHaveText('89,000');
  await expect(page.getByTestId('A-net-income')).toHaveText('37,000');

  await a.getByRole('button', {name: 'View change history'}).click();
  await expect(page.getByTestId('A-audit')).toContainText('gross_rents: 120000 → 121000');

  await page.reload();
  await expect(page.getByTestId('property-A')).toBeVisible();
  await expect(page.getByLabel('A-gross_rents')).toHaveValue('121000');
  await expect(page.getByTestId('A-net-income')).toHaveText('37,000');
});

test('shows a controlled error for non-PDF upload', async ({page}) => {
  await page.goto('/');
  await page.getByTestId('pdf-upload').setInputFiles({
    name: 'not-a-pdf.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('not a pdf'),
  });
  await expect(page.getByTestId('error-message')).toContainText('File is not a PDF');
});
