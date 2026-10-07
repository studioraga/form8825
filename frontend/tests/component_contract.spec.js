import {expect, test} from '@playwright/test';
import path from 'path';

test('LineInput supports keyboard save and escape reset', async ({page}) => {
  await page.goto('/');
  await page.getByLabel('Upload Form 8825 PDF').setInputFiles(path.resolve('../data/f8825_multi_ABC.pdf'));
  const input = page.getByLabel('A-gross_rents');
  await expect(input).toHaveValue('120000');

  await input.fill('121000');
  await input.press('Enter');
  await expect(input).toHaveValue('121000');
  await expect(page.getByTestId('A-net-income')).toHaveText('37,000');

  await input.fill('122000');
  await input.press('Escape');
  await expect(input).toHaveValue('121000');
});

test('LineInput rejects non-integer financial drafts on blur', async ({page}) => {
  await page.goto('/');
  await page.getByLabel('Upload Form 8825 PDF').setInputFiles(path.resolve('../data/f8825_multi_ABC.pdf'));
  const input = page.getByLabel('A-gross_rents');
  const persistedValue = await input.inputValue();
  await input.fill('120000.5');
  await input.press('Tab');
  await expect(input).toHaveValue(persistedValue);
});
