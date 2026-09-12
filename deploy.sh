#!/bin/bash

# 更新系统包
sudo apt update
sudo apt upgrade -y

# 安装必要的系统包
sudo apt install -y python3 python3-pip nginx git

# 安装 Python 虚拟环境
sudo apt install -y python3-venv

# 创建项目目录
mkdir -p /var/www/prompt_generator
cd /var/www/prompt_generator

# 克隆项目（需要替换为您的仓库地址）
git clone https://github.com/yuanlang12/prompt_workshop.git .

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置 Nginx
sudo cat > /etc/nginx/sites-available/prompt_generator << 'EOL'
server {
    listen 80;
    server_name your_domain.com;  # 替换为您的域名

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/prompt_generator/prompt_generator/static;
        expires 30d;
    }
}
EOL

# 启用网站配置
sudo ln -s /etc/nginx/sites-available/prompt_generator /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 测试 Nginx 配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx

# 创建 systemd 服务文件
sudo cat > /etc/systemd/system/prompt_generator.service << 'EOL'
[Unit]
Description=Prompt Generator Uvicorn Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/prompt_generator
Environment="PATH=/var/www/prompt_generator/venv/bin"
ExecStart=/var/www/prompt_generator/venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000

[Install]
WantedBy=multi-user.target
EOL

# 设置权限
sudo chown -R www-data:www-data /var/www/prompt_generator

# 启动服务
sudo systemctl daemon-reload
sudo systemctl start prompt_generator
sudo systemctl enable prompt_generator

# 显示服务状态
sudo systemctl status prompt_generator

echo "部署完成！请配置域名解析并访问您的网站。" 