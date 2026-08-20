// frontend/src/features/datasets/__tests__/DatasetUpload.test.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NextIntlClientProvider } from 'next-intl';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import messages from '../../../../messages/fr.json';
import { DatasetUpload } from '../DatasetUpload';

const pushMock = vi.fn();
vi.mock('@/i18n/routing', () => ({
  useRouter: () => ({ push: pushMock }),
}));

function renderWithProviders(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <NextIntlClientProvider locale="fr" messages={messages}>
        {ui}
      </NextIntlClientProvider>
    </QueryClientProvider>
  );
}

describe('DatasetUpload', () => {
  beforeEach(() => {
    pushMock.mockClear();
    vi.stubGlobal('fetch', vi.fn());
  });

  it('renders the drop zone with upload hint text', () => {
    renderWithProviders(<DatasetUpload />);
    expect(screen.getByText(/importer un fichier/i)).toBeInTheDocument();
    expect(screen.getByText(/glissez-déposez/i)).toBeInTheDocument();
  });

  it('rejects an unsupported file extension client-side without calling the API', async () => {
    renderWithProviders(<DatasetUpload />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const badFile = new File(['hello'], 'notes.txt', { type: 'text/plain' });

    // userEvent.upload silently filters by the input's `accept` attribute by default,
    // which would mask whether our own JS-level extension check actually runs.
    // Disable that filtering so this test exercises our validation logic, not the browser's.
    const user = userEvent.setup({ applyAccept: false });
    await user.upload(input, badFile);

    await waitFor(() => {
      expect(screen.getByText(/csv et excel/i)).toBeInTheDocument();
    });
    expect(fetch).not.toHaveBeenCalled();
  });

  it('uploads a valid CSV and navigates to the dataset detail page on success', async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 201,
      headers: { get: () => 'application/json' },
      json: async () => ({
        id: 'dataset-123',
        name: 'sales.csv',
        status: 'uploaded',
        row_count: 10,
        column_count: 3,
        columns: [],
      }),
    });

    renderWithProviders(<DatasetUpload />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const goodFile = new File(['a,b,c\n1,2,3'], 'sales.csv', { type: 'text/csv' });

    const user = userEvent.setup();
    await user.upload(input, goodFile);

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith('/datasets/dataset-123');
    });
  });
});
