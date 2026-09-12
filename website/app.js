// 提示词工坊官网脚本
'use strict';

// React 组件初始化
const brandNames = ['泼墨', '提示词工坊'];

// 移除morphing效果，只显示固定的"泼墨"文本
const BrandNameStatic = () => {
  return React.createElement(
    'span',
    {
      className: 'brand-name'
    },
    '泼墨'  // 固定显示"泼墨"
  );
};

// 在DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化品牌名称
    const logoTextElement = document.querySelector('.logo-text');
    if (logoTextElement) {
        ReactDOM.render(
            React.createElement(BrandNameStatic), // 使用静态组件
            logoTextElement
        );
    }

    // 导航栏滚动效果 - 修改为深色主题
    const header = document.querySelector('.header');
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            // 使用与深色主题一致的背景色
            header.style.backgroundColor = 'rgba(15, 18, 24, 0.95)';
            header.style.backdropFilter = 'blur(8px)';
            header.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.2)';
        } else {
            // 重置为透明背景
            header.style.backgroundColor = 'transparent';
            header.style.backdropFilter = 'none';
            header.style.boxShadow = 'none';
        }
    });

    // 移动端菜单
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    const navLinks = document.querySelector('.nav-links');
    
    if (mobileMenuToggle && navLinks) {
        mobileMenuToggle.addEventListener('click', function() {
            navLinks.classList.toggle('show');
            mobileMenuToggle.classList.toggle('active');
            
            if (mobileMenuToggle.classList.contains('active')) {
                mobileMenuToggle.innerHTML = '<i class="ri-close-line"></i>';
            } else {
                mobileMenuToggle.innerHTML = '<i class="ri-menu-line"></i>';
            }
        });
    }

    // 平滑滚动到锚点
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const target = document.querySelector(targetId);
            if (target) {
                // 关闭移动菜单（如果打开的话）
                if (navLinks && navLinks.style.display === 'flex' && window.innerWidth <= 768) {
                    navLinks.style.display = 'none';
                    mobileMenuToggle.innerHTML = '<i class="ri-menu-line"></i>';
                }
                
                // 滚动到目标位置
                window.scrollTo({
                    top: target.offsetTop - 80, // 减去导航栏的高度
                    behavior: 'smooth'
                });
            }
        });
    });

    // 价格切换（月付/年付）
    const billingToggle = document.getElementById('billing-toggle');
    const monthlyOption = document.querySelector('.switch-option:first-child');
    const yearlyOption = document.querySelector('.switch-option:last-child');
    const priceElements = document.querySelectorAll('.price');
    const originalPrices = Array.from(priceElements).map(el => el.textContent);
    
    if (billingToggle && monthlyOption && yearlyOption) {
        billingToggle.addEventListener('change', function() {
            if (this.checked) {
                // 年付
                monthlyOption.classList.remove('active');
                yearlyOption.classList.add('active');
                
                // 更新价格（按年付8折计算）
                priceElements.forEach((el, index) => {
                    if (originalPrices[index] !== '¥0') {
                        const monthlyPrice = parseInt(originalPrices[index].replace('¥', ''));
                        const yearlyPrice = Math.round(monthlyPrice * 12 * 0.8);
                        el.textContent = '¥' + yearlyPrice;
                    }
                });
                
                // 更新周期显示
                document.querySelectorAll('.period').forEach(el => {
                    el.textContent = '/年';
                });
            } else {
                // 月付
                yearlyOption.classList.remove('active');
                monthlyOption.classList.add('active');
                
                // 恢复原始价格
                priceElements.forEach((el, index) => {
                    el.textContent = originalPrices[index];
                });
                
                // 恢复周期显示
                document.querySelectorAll('.period').forEach(el => {
                    el.textContent = '/月';
                });
            }
        });
    }

    // FAQ 手风琴效果
    const faqItems = document.querySelectorAll('.faq-item');
    
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        if (question) {
            question.addEventListener('click', () => {
                // 关闭其他打开的项目
                faqItems.forEach(otherItem => {
                    if (otherItem !== item && otherItem.classList.contains('active')) {
                        otherItem.classList.remove('active');
                    }
                });
                
                // 切换当前项目状态
                item.classList.toggle('active');
            });
        }
    });

    // 轮播图
    let currentSlide = 0;
    const slides = document.querySelectorAll('.testimonial-card');
    const dots = document.querySelectorAll('.dot');
    
    if (slides.length > 0 && dots.length > 0) {
        // 显示指定的幻灯片
        function showSlide(index) {
            // 隐藏所有幻灯片
            slides.forEach(slide => {
                slide.style.display = 'none';
            });
            
            // 移除所有点的激活状态
            dots.forEach(dot => {
                dot.classList.remove('active');
            });
            
            // 显示当前幻灯片和激活对应的点
            slides[index].style.display = 'block';
            dots[index].classList.add('active');
            currentSlide = index;
        }
        
        // 初始化显示第一个幻灯片
        showSlide(0);
        
        // 点击点切换幻灯片
        dots.forEach((dot, index) => {
            dot.addEventListener('click', () => {
                showSlide(index);
            });
        });
        
        // 自动轮播
        setInterval(() => {
            let nextSlide = (currentSlide + 1) % slides.length;
            showSlide(nextSlide);
        }, 5000);
    }

    // 使用场景卡片颜色
    const useCards = document.querySelectorAll('.use-case-card');
    useCards.forEach(card => {
        const color = card.getAttribute('data-color');
        if (color) {
            card.style.borderTopColor = color;
            
            const icon = card.querySelector('.use-case-icon');
            if (icon) {
                icon.style.color = color;
            }
        }
    });

    // 动画效果
    function animateOnScroll() {
        const elements = document.querySelectorAll(
            '.feature-card, .feature-detail, .step, .use-case-card, .pricing-card, .testimonial-card, .faq-item'
        );
        
        elements.forEach(element => {
            const elementPosition = element.getBoundingClientRect().top;
            const windowHeight = window.innerHeight;
            
            // 当元素进入视口时添加淡入效果
            if (elementPosition < windowHeight - 100) {
                if (!element.classList.contains('animated')) {
                    element.style.opacity = '0';
                    element.style.animation = 'fadeInUp 0.6s forwards';
                    element.classList.add('animated');
                }
            }
        });
    }
    
    // 添加动画关键帧
    const style = document.createElement('style');
    style.innerHTML = `
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    `;
    document.head.appendChild(style);
    
    // 初始运行一次
    animateOnScroll();
    
    // 滚动时运行
    window.addEventListener('scroll', animateOnScroll);

    // 添加滚动显示效果
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('show');
            }
        });
    }, {
        threshold: 0.15
    });
    
    // 观察所有功能卡片、统计数字和功能详情
    document.querySelectorAll('.feature-card, .stat-item, .feature-detail').forEach(el => {
        observer.observe(el);
        el.classList.add('fade-in');
    });
    
    // 添加背景粒子效果
    createParticleBackground();
    
    // 添加主题切换功能
    setupThemeToggle();
});

// 创建背景粒子效果
function createParticleBackground() {
    const heroSection = document.querySelector('.hero');
    if (!heroSection) return;
    
    const particleContainer = document.createElement('div');
    particleContainer.className = 'particles-container';
    heroSection.appendChild(particleContainer);
    
    // 创建粒子
    for (let i = 0; i < 50; i++) {
        createParticle(particleContainer);
    }
}

function createParticle(container) {
    const particle = document.createElement('div');
    particle.className = 'particle';
    
    // 随机定位和大小
    const size = Math.random() * 5 + 2;
    const posX = Math.random() * 100;
    const posY = Math.random() * 100;
    const delay = Math.random() * 5;
    const duration = Math.random() * 10 + 10;
    
    particle.style.width = `${size}px`;
    particle.style.height = `${size}px`;
    particle.style.left = `${posX}%`;
    particle.style.top = `${posY}%`;
    particle.style.animationDelay = `${delay}s`;
    particle.style.animationDuration = `${duration}s`;
    
    // 随机颜色
    const colors = ['#7B61FF', '#FF5EB3', '#13EAD0'];
    const color = colors[Math.floor(Math.random() * colors.length)];
    particle.style.backgroundColor = color;
    particle.style.opacity = Math.random() * 0.5 + 0.1;
    
    container.appendChild(particle);
}

// 设置主题切换
function setupThemeToggle() {
    const root = document.documentElement;
    const isDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    // 默认使用暗色主题
    setTheme('dark');
    
    // 监听系统主题变化
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        const newTheme = e.matches ? 'dark' : 'light';
        setTheme(newTheme);
    });
    
    // 主题设置函数
    function setTheme(theme) {
        if (theme === 'dark') {
            // 深色主题已经在CSS中设置为默认
        } else {
            // 这里可以添加浅色主题的设置，但我们保持深色主题
        }
    }
}

// 为数字添加动画效果
document.addEventListener('DOMContentLoaded', function() {
    const stats = document.querySelectorAll('.stat-number');
    
    if (stats.length > 0) {
        stats.forEach(stat => {
            const target = parseInt(stat.textContent);
            const duration = 2000; // 动画持续时间（毫秒）
            const increment = target / (duration / 16); // 每帧增加的数量
            let current = 0;
            
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        animateValue(stat, 0, target, duration);
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.5 });
            
            observer.observe(stat);
        });
    }
    
    function animateValue(obj, start, end, duration) {
        let startTimestamp = null;
        const endValue = parseInt(end.toString().replace(/[^0-9]/g, ''));
        const hasPlus = end.toString().includes('+');
        
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            let value = Math.floor(progress * (endValue - start) + start);
            obj.innerHTML = hasPlus ? `${value}+` : value;
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        
        window.requestAnimationFrame(step);
    }
}); 