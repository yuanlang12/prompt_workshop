/// <reference path="../types/global.d.ts" />
import React, { useState } from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import ImproveDialog from './ImproveDialog';
import ImproveResult from './ImproveResult';
import { Prompt } from '../types/Prompt';
import { getAuthHeaders } from '../types/utils';

interface PromptCardProps {
    prompt: Prompt;
}

const PromptCard: React.FC<PromptCardProps> = ({ prompt }) => {
    const [isImproveDialogOpen, setImproveDialogOpen] = useState(false);
    const [improveResult, setImproveResult] = useState(null);

    const handleImprove = async (improveInstructions: string) => {
        try {
            const response = await fetch('/improve', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders()
                } as Record<string, string>,
                credentials: 'include',
                body: JSON.stringify({
                    project_id: prompt.project_id,
                    prompt_id: prompt.id,
                    metaprompt: prompt.system_prompt || prompt.content,
                    improve_instructions: improveInstructions
                })
            });
            
            if (!response.ok) {
                throw new Error('优化失败');
            }
            
            const data = await response.json();
            setImproveResult(data);
        } catch (error) {
            console.error('优化出错:', error);
            // TODO: 添加错误提示
        }
    };

    return (
        <Card sx={{ mb: 2 }}>
            <CardContent>
                <Typography variant="h6" gutterBottom>
                    版本: {prompt.version}
                </Typography>
                <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" color="text.secondary">
                        变量: {prompt.variables.length ? prompt.variables.join(', ') : '无'}
                    </Typography>
                </Box>
                
                {/* System Prompt */}
                <Typography variant="subtitle2" color="text.primary" sx={{ mb: 1 }}>
                    System Prompt:
                </Typography>
                <Box 
                    sx={{ 
                        p: 2, 
                        bgcolor: 'background.paper',
                        border: '1px solid',
                        borderColor: 'divider',
                        borderRadius: 1,
                        mb: 2,
                        maxHeight: '200px',
                        overflow: 'auto',
                        whiteSpace: 'pre-wrap'
                    }}
                >
                    <Typography variant="body2" component="pre">
                        {prompt.system_prompt || prompt.content || '(空)'}
                    </Typography>
                </Box>
                
                {/* User Prompt (如果存在) */}
                {prompt.user_prompt && (
                    <>
                        <Typography variant="subtitle2" color="text.primary" sx={{ mb: 1 }}>
                            User Prompt:
                        </Typography>
                        <Box 
                            sx={{ 
                                p: 2, 
                                bgcolor: 'background.paper',
                                border: '1px solid',
                                borderColor: 'divider',
                                borderRadius: 1,
                                mb: 2,
                                maxHeight: '150px',
                                overflow: 'auto',
                                whiteSpace: 'pre-wrap'
                            }}
                        >
                            <Typography variant="body2" component="pre">
                                {prompt.user_prompt}
                            </Typography>
                        </Box>
                    </>
                )}
                
                <Box display="flex" justifyContent="space-between">
                    <Button 
                        variant="outlined" 
                        size="small"
                        onClick={() => setImproveDialogOpen(true)}
                    >
                        优化
                    </Button>
                </Box>
            </CardContent>

            {/* 优化对话框 */}
            <ImproveDialog 
                isOpen={isImproveDialogOpen}
                onClose={() => setImproveDialogOpen(false)}
                onSubmit={handleImprove}
                promptContent={prompt.system_prompt || prompt.content}
                projectId={prompt.project_id}
            />

            {/* 优化结果 */}
            {improveResult && (
                <ImproveResult 
                    result={improveResult}
                    projectId={prompt.project_id}
                    onClose={() => setImproveResult(null)}
                    onSaved={() => {
                        setImproveResult(null);
                        setImproveDialogOpen(false);
                    }}
                    onReEdit={() => {
                        setImproveResult(null);
                        setImproveDialogOpen(true);
                    }}
                />
            )}
        </Card>
    );
};

export default PromptCard; 