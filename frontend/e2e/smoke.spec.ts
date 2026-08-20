// frontend/e2e/smoke.spec.ts
/**
 * E2E smoke path required by section 15: login -> upload -> clean -> descriptive -> regression.
 *
 * Prerequisites (not started by this file):
 *   - The backend stack running against a real Postgres/Redis: `docker-compose up postgres redis backend worker`
 *   - The frontend dev server: `npm run dev` (or PLAYWRIGHT_BASE_URL pointing at a running instance)
 *   - Browser binaries installed: `npx playwright install chromium`
 *
 * Each run registers a fresh throwaway company/user (randomized email) so the
 * test is independent and repeatable against a persistent dev database.
 */
import { expect, test } from '@playwright/test';
import path from 'path';

const FIXTURE_CSV = path.join(__dirname, 'fixtures', 'sample-sales.csv');

function uniqueEmail(): string {
  return `e2e-${Date.now()}-${Math.floor(Math.random() * 10000)}@smoketest.dz`;
}

test('login -> upload -> clean -> descriptive -> regression', async ({ page }) => {
  const email = uniqueEmail();

  // --- 1. Register (creates the company + first user, then logs in) ---
  await page.goto('/fr/register');
  await page.getByLabel("Nom de l'entreprise").fill('E2E Smoke Test Co');
  await page.getByLabel('Nom complet').fill('E2E Tester');
  await page.getByLabel('Adresse e-mail').fill(email);
  await page.getByLabel('Mot de passe').fill('SmokeTest1234!');
  await page.getByRole('button', { name: 'Créer le compte' }).click();

  await expect(page).toHaveURL(/\/fr\/dashboard/, { timeout: 15_000 });

  // --- 2. Upload a dataset ---
  await page.goto('/fr/datasets');
  await page.locator('input[type="file"]').setInputFiles(FIXTURE_CSV);

  // Successful upload redirects to the dataset detail page (/datasets/{id}).
  await expect(page).toHaveURL(/\/fr\/datasets\/[0-9a-f-]{36}/, { timeout: 20_000 });

  // --- 3. Clean the dataset ---
  await page.goto('/fr/cleaning');
  await page.getByRole('combobox').click();
  await page.getByRole('option', { name: /sample-sales/ }).click();
  await expect(page.getByRole('button', { name: 'Lancer le nettoyage' })).toBeVisible();
  await page.getByRole('button', { name: 'Lancer le nettoyage' }).click();
  await expect(page.getByText('Lignes avant')).toBeVisible({ timeout: 20_000 });

  // --- 4. Descriptive statistics ---
  await page.goto('/fr/analytics');
  await page.getByRole('combobox').click();
  await page.getByRole('option', { name: /sample-sales/ }).click();
  await page.getByRole('button', { name: 'Lancer les statistiques descriptives' }).click();
  await expect(page.getByText(/lignes analysees/)).toBeVisible({ timeout: 20_000 });

  // --- 5. Regression ---
  await page.getByRole('tab', { name: 'Regression' }).click();
  // Target variable select (first combobox in the regression panel)
  await page.getByText('Variable cible').locator('..').getByRole('combobox').click();
  await page.getByRole('option', { name: 'sales', exact: true }).click();
  // Feature checkboxes
  await page.getByLabel('marketing_spend').check();
  await page.getByLabel('price').check();
  await page.getByRole('button', { name: 'Lancer la regression' }).click();

  await expect(page.getByText('R2', { exact: true })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(/Modele enregistre/)).toBeVisible();
});
