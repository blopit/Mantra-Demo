import React, { useState } from 'react';
import type { FC } from 'react';
import type { Button as MuiButton, Box as MuiBox, Typography as MuiTypography, TextField as MuiTextField } from '@mui/material';
import { Button, Box, Typography, TextField } from '@mui/material';
import type { useSnackbar as UseSnackbar } from 'notistack';
import { useSnackbar } from 'notistack';

const WorkflowCreator: FC = () => {
  const { enqueueSnackbar } = useSnackbar();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const handleCreateWorkflow = async () => {
    try {
      // First get the transformed workflow
      const transformResponse = await fetch('/api/mantras/test-workflow', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const transformData = await transformResponse.json();

      if (!transformResponse.ok) {
        throw new Error(transformData.detail || 'Failed to transform workflow');
      }

      // Now create the actual workflow
      const createResponse = await fetch('/api/mantras/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name,
          description,
          workflow_json: transformData.workflow,
          user_id: '118212762049438290784' // This should come from your auth context
        }),
      });

      const createData = await createResponse.json();

      if (!createResponse.ok) {
        throw new Error(createData.detail || 'Failed to create workflow');
      }

      enqueueSnackbar('Workflow created successfully!', {
        variant: 'success',
      });
      
      // Reset form
      setName('');
      setDescription('');
      
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
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 400, mb: 2 }}>
        <TextField
          label="Workflow Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <TextField
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          multiline
          rows={3}
          required
        />
      </Box>
      <Button
        variant="contained"
        color="primary"
        onClick={handleCreateWorkflow}
        disabled={!name || !description}
      >
        Create Workflow
      </Button>
    </Box>
  );
};

export default WorkflowCreator; 