/**
 * 全局类型声明文件
 * 用于声明外部模块，解决类型不存在的问题
 */

// 声明React模块类型
declare module 'react' {
  export function useState<T>(initialState: T | (() => T)): [T, (newState: T | ((prevState: T) => T)) => void];
  export const useEffect: any;
  export const useCallback: any;
  export const useMemo: any;
  export const useRef: any;
  export type FC<P = {}> = FunctionComponent<P>;
  export interface FunctionComponent<P = {}> {
    (props: P): any;
  }
}

// 添加JSX命名空间支持
declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}

// 声明Material-UI组件类型
declare module '@mui/material/Card' {
  const Card: any;
  export default Card;
}

declare module '@mui/material/CardContent' {
  const CardContent: any;
  export default CardContent;
}

declare module '@mui/material/Button' {
  const Button: any;
  export default Button;
}

declare module '@mui/material/Typography' {
  const Typography: any;
  export default Typography;
}

declare module '@mui/material/Box' {
  const Box: any;
  export default Box;
}

declare module '@mui/material/Paper' {
  const Paper: any;
  export default Paper;
}

declare module '@mui/material/CircularProgress' {
  const CircularProgress: any;
  export default CircularProgress;
}

declare module '@mui/material/Alert' {
  const Alert: any;
  export default Alert;
}

declare module '@mui/material/Stepper' {
  const Stepper: any;
  export default Stepper;
}

declare module '@mui/material/Step' {
  const Step: any;
  export default Step;
}

declare module '@mui/material/StepLabel' {
  const StepLabel: any;
  export default StepLabel;
}

declare module '@mui/material/StepContent' {
  const StepContent: any;
  export default StepContent;
}

// 声明Dialog相关组件
declare module '@mui/material/Dialog' {
  const Dialog: any;
  export default Dialog;
}

declare module '@mui/material/DialogTitle' {
  const DialogTitle: any;
  export default DialogTitle;
}

declare module '@mui/material/DialogContent' {
  const DialogContent: any;
  export default DialogContent;
}

declare module '@mui/material/DialogActions' {
  const DialogActions: any;
  export default DialogActions;
}

declare module '@mui/material/TextField' {
  const TextField: any;
  export default TextField;
} 