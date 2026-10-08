// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
import { defineLiveCollection } from 'astro:content';
import { emdashLoader } from 'emdash/runtime';

export const collections = {
  _emdash: defineLiveCollection({ loader: emdashLoader() }),
};
