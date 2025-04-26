import React from 'react';
import type { FC } from 'react';
import type { Button as MuiButton, Box as MuiBox, Typography as MuiTypography } from '@mui/material';
import { Button, Box, Typography } from '@mui/material';
import type { useSnackbar as UseSnackbar } from 'notistack';
import { useSnackbar } from 'notistack';

const WorkflowCreator: FC = () => {
  const { enqueueSnackbar } = useSnackbar();

  const handleCreateWorkflow = async () => {
    try {
      const response = await fetch('/api/mantras/test-workflow', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to create workflow');
      }

      // Log the transformed workflow to console
      console.log('Transformed Workflow:', data.workflow);
      
      enqueueSnackbar('Workflow transformed successfully! Check console for details.', {
        variant: 'success',
      });
      
    } catch (error) {
      console.error('Error creating workflow:', error);
      enqueueSnackbar(`Failed to create workflow: ${(error as Error).message}`, {
        variant: 'error',
      });
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        Workflow Creator
      </Typography>
      <Button
        variant="contained"
        color="primary"
        onClick={handleCreateWorkflow}
      >
        Create Test Workflow
      </Button>
    </Box>
  );
};

export default WorkflowCreator; 