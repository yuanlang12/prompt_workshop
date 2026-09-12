import React, { useState, useEffect } from 'react';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import VersionTabs from './VersionTabs';
import PromptCard from './PromptCard';

interface Prompt {
    id: string;
    project_id: string;
    content: string;
    variables: string[];
    version: string;
}

interface PromptVersionsProps {
    prompts: Prompt[];
    onPromptSelect: (prompt: Prompt) => void;
}

const PromptVersions: React.FC<PromptVersionsProps> = ({ prompts, onPromptSelect }) => {
    const [currentVersionId, setCurrentVersionId] = useState<string>('');
    const [currentPrompt, setCurrentPrompt] = useState<Prompt | null>(null);

    useEffect(() => {
        if (prompts.length > 0) {
            // 默认选择最新版本
            const latestPrompt = prompts[prompts.length - 1];
            setCurrentVersionId(latestPrompt.id);
            setCurrentPrompt(latestPrompt);
            onPromptSelect(latestPrompt);
        }
    }, [prompts]);

    const handleVersionChange = (versionId: string) => {
        const selectedPrompt = prompts.find(p => p.id === versionId);
        if (selectedPrompt) {
            setCurrentVersionId(versionId);
            setCurrentPrompt(selectedPrompt);
            onPromptSelect(selectedPrompt);
        }
    };

    if (prompts.length === 0) {
        return (
            <Box sx={{ p: 2, color: '#888' }}>
                当前项目还没有提示词版本
            </Box>
        );
    }

    return (
        <Paper 
            elevation={0} 
            sx={{ 
                bgcolor: 'transparent',
                height: '100%',
                display: 'flex',
                flexDirection: 'column'
            }}
        >
            <VersionTabs
                versions={prompts}
                currentVersion={currentVersionId}
                onVersionChange={handleVersionChange}
            />
            
            <Box sx={{ 
                flex: 1,
                overflow: 'auto',
                bgcolor: '#2d2d2d',
                borderRadius: '4px',
                p: 2
            }}>
                {currentPrompt && <PromptCard prompt={currentPrompt} />}
            </Box>
        </Paper>
    );
};

export default PromptVersions; 