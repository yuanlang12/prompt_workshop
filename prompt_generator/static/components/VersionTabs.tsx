import React from 'react';
import Box from '@mui/material/Box';
import FormControl from '@mui/material/FormControl';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import InputLabel from '@mui/material/InputLabel';

interface VersionTabsProps {
    versions: Array<{
        id: string;
        version: string;
    }>;
    currentVersion: string;
    onVersionChange: (version: string) => void;
}

const VersionTabs: React.FC<VersionTabsProps> = ({ versions, currentVersion, onVersionChange }) => {
    const handleChange = (event: any) => {
        onVersionChange(event.target.value);
    };

    return (
        <Box sx={{ mb: 2 }}>
            <FormControl 
                fullWidth
                variant="outlined"
                sx={{
                    '& .MuiOutlinedInput-root': {
                        color: '#e0e0e0',
                        '& fieldset': {
                            borderColor: 'rgba(255, 255, 255, 0.23)',
                        },
                        '&:hover fieldset': {
                            borderColor: '#4a9eff',
                        },
                        '&.Mui-focused fieldset': {
                            borderColor: '#4a9eff',
                        },
                    },
                    '& .MuiInputLabel-root': {
                        color: '#e0e0e0',
                        '&.Mui-focused': {
                            color: '#4a9eff',
                        },
                    },
                    '& .MuiSelect-icon': {
                        color: '#e0e0e0',
                    },
                }}
            >
                <InputLabel id="version-select-label">选择版本</InputLabel>
                <Select
                    labelId="version-select-label"
                    value={currentVersion}
                    onChange={handleChange}
                    label="选择版本"
                    MenuProps={{
                        PaperProps: {
                            sx: {
                                bgcolor: '#333',
                                '& .MuiMenuItem-root': {
                                    color: '#e0e0e0',
                                    '&:hover': {
                                        bgcolor: 'rgba(74, 158, 255, 0.1)',
                                    },
                                    '&.Mui-selected': {
                                        bgcolor: 'rgba(74, 158, 255, 0.2)',
                                        '&:hover': {
                                            bgcolor: 'rgba(74, 158, 255, 0.3)',
                                        },
                                    },
                                },
                            },
                        },
                    }}
                >
                    {versions.map((version) => (
                        <MenuItem key={version.id} value={version.id}>
                            版本 {version.version}
                        </MenuItem>
                    ))}
                </Select>
            </FormControl>
        </Box>
    );
};

export default VersionTabs; 