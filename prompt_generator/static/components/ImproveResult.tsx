/// <reference path="../types/global.d.ts" />
import React, { useState } from 'react';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Stepper from '@mui/material/Stepper';
import Step from '@mui/material/Step';
import StepLabel from '@mui/material/StepLabel';
import StepContent from '@mui/material/StepContent';
import { getAuthHeaders } from '../types/utils';

interface ImproveResultProps {
    result: {
        planning: string;
        writing_prompts: string;
        variables: string[];
        modification_plan?: string;
        final_prompt?: string;
    };
    projectId: string;
    onClose: () => void;
    onSaved?: () => void;
    onReEdit: () => void;
}

const ImproveResult: React.FC<ImproveResultProps> = ({ result, projectId, onClose, onSaved, onReEdit }) => {
    const [activeStep, setActiveStep] = useState(0);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // 定义步骤
    const steps = [
        { 
            label: '优化思路分析', 
            content: result.planning,
            description: '优化思路分析提供了提示词的优化方向和改进点，揭示潜在问题并提出解决方案。'
        },
        { 
            label: '优化后提示词', 
            content: result.writing_prompts || result.final_prompt || '',
            description: '这是依据优化思路生成的优化版本，包含更清晰的指令和更合理的结构。'
        }
    ];

    const handleNext = () => {
        setActiveStep((prevStep) => prevStep + 1);
    };

    const handleBack = () => {
        setActiveStep((prevStep) => prevStep - 1);
    };

    const handleSave = async () => {
        if (!result.final_prompt) return;
        
        setSaving(true);
        setError(null);
        
        try {
            const response = await fetch('/api/prompts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders()
                } as Record<string, string>,
                credentials: 'include',
                body: JSON.stringify({
                    project_id: projectId,
                    system_prompt: result.final_prompt,
                    user_prompt: '',
                    variables: result.variables ?? []
                })
            });

            if (!response.ok) {
                throw new Error('保存失败');
            }

            await response.json();
            onSaved?.();
            onClose();
        } catch (error) {
            setError(error instanceof Error ? error.message : '保存失败');
        } finally {
            setSaving(false);
        }
    };

    return (
        <Paper 
            elevation={3} 
            sx={{ 
                p: 3, 
                mt: 2, 
                bgcolor: 'background.paper', 
                position: 'relative',
                maxHeight: '80vh',
                overflow: 'auto'
            }}
        >
            <Box sx={{ position: 'absolute', top: 10, right: 10 }}>
                <Button 
                    onClick={onClose}
                    size="small"
                    sx={{ minWidth: 'auto', p: '4px', lineHeight: 1 }}
                >
                    ✕
                </Button>
            </Box>

            <Typography variant="h5" gutterBottom sx={{ mb: 3 }}>
                提示词优化结果
            </Typography>

            {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                    {error}
                </Alert>
            )}

            <Stepper activeStep={activeStep} orientation="vertical">
                {steps.map((step, index) => (
                    <Step key={index}>
                        <StepLabel>
                            <Typography variant="subtitle1">{step.label}</Typography>
                        </StepLabel>
                        <StepContent>
                            <Typography variant="body2" color="text.secondary" paragraph>
                                {step.description}
                            </Typography>
                            <Box 
                                sx={{ 
                                    p: 2, 
                                    bgcolor: 'background.default',
                                    border: '1px solid',
                                    borderColor: 'divider',
                                    borderRadius: 1,
                                    mb: 2,
                                    whiteSpace: 'pre-wrap',
                                    maxHeight: '300px',
                                    overflow: 'auto'
                                }}
                            >
                                <Typography 
                                    variant="body2" 
                                    component="pre" 
                                    sx={{ 
                                        margin: 0,
                                        fontFamily: 'monospace'
                                    }}
                                >
                                    {step.content}
                                </Typography>
                            </Box>
                            <Box sx={{ mb: 2 }}>
                                <div>
                                    <Button
                                        disabled={index === 0}
                                        onClick={handleBack}
                                        sx={{ mr: 1 }}
                                    >
                                        上一步
                                    </Button>
                                    <Button
                                        variant="contained"
                                        onClick={index === steps.length - 1 ? handleSave : handleNext}
                                        disabled={saving}
                                    >
                                        {index === steps.length - 1 ? (
                                            saving ? (
                                                <CircularProgress size={24} color="inherit" />
                                            ) : '保存此版本'
                                        ) : '下一步'}
                                    </Button>
                                    {index === steps.length - 1 && (
                                        <Button
                                            variant="outlined"
                                            onClick={onReEdit}
                                            sx={{ ml: 1 }}
                                            disabled={saving}
                                        >
                                            继续编辑
                                        </Button>
                                    )}
                                </div>
                            </Box>
                        </StepContent>
                    </Step>
                ))}
            </Stepper>
        </Paper>
    );
};

export default ImproveResult; 
