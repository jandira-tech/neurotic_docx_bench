// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only

type Theme = 'light' | 'dark';
const root = document.documentElement;
const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
const controls = document.querySelectorAll<HTMLButtonElement>('[data-theme-choice]');
let chosenTheme = root.dataset.theme as Theme | undefined;

function renderTheme() {
  const theme = chosenTheme ?? (systemTheme.matches ? 'dark' : 'light');
  root.dataset.theme = theme;
  controls.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.themeChoice === theme)));
  document.querySelector<HTMLMetaElement>('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#17212b' : '#f5f5f2');
}

controls.forEach((button) => button.addEventListener('click', () => {
  chosenTheme = button.dataset.themeChoice as Theme;
  renderTheme();
  // Keep the control usable when browser storage is disabled.
  try { localStorage.setItem('jb-theme', chosenTheme); } catch {}
}));

systemTheme.addEventListener('change', () => { if (!chosenTheme) renderTheme(); });
window.addEventListener('storage', (event) => {
  if (event.key !== 'jb-theme' && event.key !== null) return;
  chosenTheme = event.newValue === 'light' || event.newValue === 'dark' ? event.newValue : undefined;
  renderTheme();
});
renderTheme();
