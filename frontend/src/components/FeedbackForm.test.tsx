import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import FeedbackForm from './FeedbackForm';

describe('FeedbackForm', () => {
  it('accepts short customer feedback once it reaches the minimum threshold', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    render(<FeedbackForm onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText(/your feedback/i), 'u sure?');
    await user.click(screen.getByRole('button', { name: /submit feedback/i }));

    expect(onSubmit).toHaveBeenCalledWith({
      feedback_type: 'question',
      content: 'u sure?',
    });
  });
});
