import React, { useState, useEffect } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import ImproveResult from './ImproveResult';

interface ImproveDialogProps {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (instructions: string) => Promise<any>;
    promptContent: string;
    projectId: string;
}

const ImproveDialog: React.FC<ImproveDialogProps> = ({
    isOpen,
    onClose,
    onSubmit,
    promptContent,
    projectId
}) => {
    const [instructions, setInstructions] = useState('');
    const [improveResult, setImproveResult] = useState<any>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    // 重置状态
    const resetState = () => {
        setImproveResult(null);
        setIsSubmitting(false);
    };

    // 处理重新编辑
    const handleReEdit = () => {
        // 只重置结果，保留指令内容
        setImproveResult(null);
        setIsSubmitting(false);
    };

    // 处理提交
    const handleSubmit = async () => {
        if (!instructions.trim()) {
            return;
        }

        setIsSubmitting(true);
        try {
            const result = await onSubmit(instructions);
            setImproveResult(result);
        } catch (error) {
            console.error('优化失败:', error);
            // TODO: 添加错误提示
        } finally {
            setIsSubmitting(false);
        }
    };

    // 处理关闭
    const handleClose = () => {
        // 完全重置所有状态
        resetState();
        setInstructions('');
        onClose();
    };

    // 处理保存成功
    const handleSaved = () => {
        handleClose();
    };

    return (
        <Dialog
            open={isOpen}
            onClose={handleClose}
            maxWidth="md"
            fullWidth
        >
            {!improveResult ? (
                <>
                    <DialogTitle>优化提示词</DialogTitle>
                    <DialogContent>
                        <Box sx={{ mb: 2 }}>
                            <Typography variant="subtitle1" gutterBottom>
                                当前提示词：
                            </Typography>
                            <Box sx={{
                                bgcolor: '#f5f5f5',
                                p: 2,
                                borderRadius: 1,
                                maxHeight: '200px',
                                overflow: 'auto'
                            }}>
                                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                                    {promptContent}
                                </pre>
                            </Box>
                        </Box>
                        <TextField
                            fullWidth
                            multiline
                            rows={4}
                            label="优化指令"
                            value={instructions}
                            onChange={(e) => setInstructions(e.target.value)}
                            placeholder="请输入优化指令..."
                            disabled={isSubmitting}
                        />
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={handleClose} disabled={isSubmitting}>
                            取消
                        </Button>
                        <Button
                            onClick={handleSubmit}
                            variant="contained"
                            disabled={!instructions.trim() || isSubmitting}
                        >
                            {isSubmitting ? '优化中...' : '确认优化'}
                        </Button>
                    </DialogActions>
                </>
            ) : (
                <DialogContent>
                    <ImproveResult
                        result={improveResult}
                        projectId={projectId}
                        onClose={handleClose}
                        onSaved={handleSaved}
                        onReEdit={handleReEdit}
                    />
                </DialogContent>
            )}
        </Dialog>
    );
};

export default ImproveDialog; 