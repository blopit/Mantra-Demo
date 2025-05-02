import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SnackbarProvider } from 'notistack';
import WorkflowCreator from '../WorkflowCreator';

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock sample workflow data
const sampleWorkflowData = {
  workflow: {
    nodes: [
      {
        id: '1',
        type: 'gmail',
        name: 'Send Email',
        parameters: {
          operation: 'sendEmail',
          to: '${trigger.email}',
          subject: 'Welcome to Mantra!',
          text: 'Thanks for trying out our workflow automation!'
        }
      }
    ]
  }
};

describe('WorkflowCreator', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  const renderWithSnackbar = () => {
    return render(
      <SnackbarProvider>
        <WorkflowCreator />
      </SnackbarProvider>
    );
  };

  describe('Form Validation', () => {
    it('should disable submit button when fields are empty', () => {
      renderWithSnackbar();
      const submitButton = screen.getByRole('button', { name: /create workflow/i });
      expect(submitButton).toBeDisabled();
    });

    it('should enable submit button when all fields are filled', () => {
      renderWithSnackbar();
      const nameInput = screen.getByLabelText(/workflow name/i);
      const descInput = screen.getByLabelText(/description/i);

      fireEvent.change(nameInput, { target: { value: 'Test Workflow' } });
      fireEvent.change(descInput, { target: { value: 'Test Description' } });

      const submitButton = screen.getByRole('button', { name: /create workflow/i });
      expect(submitButton).not.toBeDisabled();
    });
  });

  describe('API Interaction', () => {
    it('should handle successful workflow creation', async () => {
      // Mock successful API responses
      mockFetch
        .mockImplementationOnce(() => Promise.resolve({
          ok: true,
          json: () => Promise.resolve(sampleWorkflowData)
        }))
        .mockImplementationOnce(() => Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ id: '123', name: 'Test Workflow' })
        }));

      renderWithSnackbar();

      // Fill out form
      fireEvent.change(screen.getByLabelText(/workflow name/i), {
        target: { value: 'Test Workflow' }
      });
      fireEvent.change(screen.getByLabelText(/description/i), {
        target: { value: 'Test Description' }
      });

      // Submit form
      fireEvent.click(screen.getByRole('button', { name: /create workflow/i }));

      // Verify API calls
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(2);
        expect(mockFetch).toHaveBeenCalledWith('/api/mantras/test-workflow', expect.any(Object));
        expect(mockFetch).toHaveBeenCalledWith('/api/mantras/', expect.any(Object));
      });

      // Verify form reset
      await waitFor(() => {
        expect(screen.getByLabelText(/workflow name/i)).toHaveValue('');
        expect(screen.getByLabelText(/description/i)).toHaveValue('');
      });
    });

    it('should handle workflow transformation error', async () => {
      // Mock failed transformation
      mockFetch.mockImplementationOnce(() => Promise.resolve({
        ok: false,
        json: () => Promise.resolve({ detail: 'Transform failed' })
      }));

      renderWithSnackbar();

      // Fill out form
      fireEvent.change(screen.getByLabelText(/workflow name/i), {
        target: { value: 'Test Workflow' }
      });
      fireEvent.change(screen.getByLabelText(/description/i), {
        target: { value: 'Test Description' }
      });

      // Submit form
      fireEvent.click(screen.getByRole('button', { name: /create workflow/i }));

      // Verify error handling
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(1);
        expect(mockFetch).toHaveBeenCalledWith('/api/mantras/test-workflow', expect.any(Object));
      });

      // Form should not be reset on error
      expect(screen.getByLabelText(/workflow name/i)).toHaveValue('Test Workflow');
      expect(screen.getByLabelText(/description/i)).toHaveValue('Test Description');
    });

    it('should handle workflow creation error', async () => {
      // Mock successful transformation but failed creation
      mockFetch
        .mockImplementationOnce(() => Promise.resolve({
          ok: true,
          json: () => Promise.resolve(sampleWorkflowData)
        }))
        .mockImplementationOnce(() => Promise.resolve({
          ok: false,
          json: () => Promise.resolve({ detail: 'Creation failed' })
        }));

      renderWithSnackbar();

      // Fill out form
      fireEvent.change(screen.getByLabelText(/workflow name/i), {
        target: { value: 'Test Workflow' }
      });
      fireEvent.change(screen.getByLabelText(/description/i), {
        target: { value: 'Test Description' }
      });

      // Submit form
      fireEvent.click(screen.getByRole('button', { name: /create workflow/i }));

      // Verify error handling
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(2);
        expect(mockFetch).toHaveBeenCalledWith('/api/mantras/test-workflow', expect.any(Object));
        expect(mockFetch).toHaveBeenCalledWith('/api/mantras/', expect.any(Object));
      });

      // Form should not be reset on error
      expect(screen.getByLabelText(/workflow name/i)).toHaveValue('Test Workflow');
      expect(screen.getByLabelText(/description/i)).toHaveValue('Test Description');
    });
  });
}); 