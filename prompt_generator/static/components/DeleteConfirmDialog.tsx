import React, { useState } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';

interface DeleteConfirmDialogProps {
    isOpen: boolean;
    projectName: string;
    onClose: () => void;
    onConfirm: () => Promise<void>;
}

const DeleteConfirmDialog: React.FC<DeleteConfirmDialogProps> = ({
    isOpen,
    projectName,
    onClose,
    onConfirm
}) => {
    const [isDeleting, setIsDeleting] = useState(false);

    const handleConfirm = async () => {
        setIsDeleting(true);
        try {
            await onConfirm();
            onClose();
        } catch (error) {
            console.error('删除失败:', error);
        } finally {
            setIsDeleting(false);
        }
    };

    return (
        <Dialog
            open={isOpen}
            onClose={!isDeleting ? onClose : undefined}
            aria-labelledby="delete-dialog-title"
            aria-describedby="delete-dialog-description"
        >
            <DialogTitle id="delete-dialog-title" sx={{ color: '#333' }}>
                确认删除项目
            </DialogTitle>
            <DialogContent>
                <DialogContentText id="delete-dialog-description" sx={{ color: '#666' }}>
                    确定要删除项目 "{projectName}" 吗？此操作不可恢复。
                </DialogContentText>
            </DialogContent>
            <DialogActions>
                <Button 
                    onClick={onClose} 
                    disabled={isDeleting}
                    sx={{ color: '#666' }}
                >
                    取消
                </Button>
                <Button
                    onClick={handleConfirm}
                    color="error"
                    variant="contained"
                    disabled={isDeleting}
                    startIcon={isDeleting ? <CircularProgress size={20} /> : null}
                >
                    {isDeleting ? '删除中...' : '确认删除'}
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default DeleteConfirmDialog; 