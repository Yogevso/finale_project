import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AxiosError } from 'axios';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import LoginPage from '../pages/LoginPage';
import { AuthProvider } from '../lib/auth';

const authMocks = vi.hoisted(() => ({
  login: vi.fn(),
}));

const authState = vi.hoisted(() => ({
  user: null as { role: string } | null,
  isLoading: false,
}));

const navigateMock = vi.hoisted(() => vi.fn());

// Mock navigate
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock('../lib/auth', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
  useAuth: () => ({
    user: authState.user,
    isLoading: authState.isLoading,
    login: authMocks.login,
    register: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
    isSystemAdmin: false,
    isAdmin: false,
    isManager: false,
    isEditor: false,
    isViewer: false,
    isCustomer: false,
    isInternal: false,
    hasPermission: vi.fn(() => false),
    canEditDocuments: false,
    canPublishDocuments: false,
    canManageUsers: false,
    canManageCompanies: false,
  }),
}));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const renderWithProviders = (component: React.ReactNode) => {
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          {component}
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

describe('LoginPage', () => {
  beforeEach(() => {
    authMocks.login.mockReset();
    authState.user = null;
    authState.isLoading = false;
    navigateMock.mockReset();
    window.history.pushState({}, '', '/login');
  });

  it('renders login form', () => {
    renderWithProviders(<LoginPage />);
    
    expect(screen.getByText(/Sign in to your account/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Password$/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sign in/i })).toBeInTheDocument();
  });

  it('renders demo credentials', () => {
    renderWithProviders(<LoginPage />);
    
    expect(screen.getByText(/Demo Credentials/i)).toBeInTheDocument();
    expect(screen.getByText(/admin \/ admin123/i)).toBeInTheDocument();
  });

  it('shows Documentation Platform title', () => {
    renderWithProviders(<LoginPage />);
    
    expect(screen.getByText(/Documentation Platform/i)).toBeInTheDocument();
  });

  it('shows a network-specific error when login fails before a response is received', async () => {
    const user = userEvent.setup();
    authMocks.login.mockRejectedValueOnce(new AxiosError('Network Error', 'ERR_NETWORK'));

    renderWithProviders(<LoginPage />);

    await user.type(screen.getByLabelText(/Username/i), 'testuser');
    await user.type(screen.getByPlaceholderText(/Enter your password/i), 'testpass123');
    await user.click(screen.getByRole('button', { name: /Sign in/i }));

    expect(
      await screen.findByText(/A network error occurred\. Please check your connection and try again\./i),
    ).toBeInTheDocument();
  });

  it('redirects authenticated users to the requested next path after login', async () => {
    authState.user = { role: 'editor' };
    window.history.pushState({}, '', '/login?next=%2Fdocuments%3Fpage%3D2');

    renderWithProviders(<LoginPage />);

    expect(navigateMock).toHaveBeenCalledWith('/documents?page=2', { replace: true });
  });

  it('ignores unsafe external next paths and falls back to the role home route', async () => {
    authState.user = { role: 'editor' };
    window.history.pushState({}, '', '/login?next=https%3A%2F%2Fevil.example');

    renderWithProviders(<LoginPage />);

    expect(navigateMock).toHaveBeenCalledWith('/dashboard', { replace: true });
  });
});
