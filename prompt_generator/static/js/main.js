document.addEventListener("DOMContentLoaded", function () {
    // HTML转义函数 - 移到前面确保先定义
    function escapeHtml(text) {
        if (!text) return "";
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // 显示通知函数
    function showNotification(message, type = "info") {
        console.log(`通知: ${message} (${type})`);

        const notification = document.createElement("div");
        // Using Tailwind for styling
        const typeClasses = {
            success: "bg-emerald-50 text-emerald-800 border-emerald-100",
            error: "bg-rose-50 text-rose-800 border-rose-100",
            warning: "bg-amber-50 text-amber-800 border-amber-100",
            info: "bg-stone-50 text-stone-800 border-stone-100"
        };

        notification.className = `fixed bottom-6 right-6 px-5 py-3 rounded-xl border bg-white shadow-xl z-[2000] flex items-center gap-3 transform translate-y-4 opacity-0 transition-all duration-200 ease-out ${typeClasses[type] || typeClasses.info}`;
        notification.innerHTML = `
            <i class="${getNotificationIcon(type)} text-xl"></i>
            <span class="text-sm font-medium tracking-tight">${message}</span>
        `;

        document.body.appendChild(notification);

        // Use requestAnimationFrame for smoother start
        requestAnimationFrame(() => {
            notification.classList.remove("translate-y-4", "opacity-0");
        });

        // Fade out and remove (200ms transition per UI-Skills)
        setTimeout(() => {
            notification.classList.add("opacity-0", "translate-y-2");
            setTimeout(() => {
                if (notification.parentNode) document.body.removeChild(notification);
            }, 200);
        }, 3000);
    }

    // 获取通知图标
    function getNotificationIcon(type) {
        switch (type) {
            case "success": return "ri-check-line";
            case "error": return "ri-error-warning-line";
            case "warning": return "ri-alert-line";
            default: return "ri-information-line";
        }
    }

    // 复制文本到剪贴板
    function copyToClipboard(text) {
        // 创建临时textarea元素
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed";  // 防止滚动到底部
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();

        try {
            // 执行复制命令
            const successful = document.execCommand("copy");
            if (!successful) {
                console.error("复制失败");
            }
        } catch (err) {
            console.error("复制出错:", err);
        }

        // 移除临时元素
        document.body.removeChild(textarea);
    }

    // 获取DOM元素
    const taskDescription = document.querySelector("#task-description");
    // 变量输入功能已移至生成提示词弹窗中
    const generatePromptBtn = document.querySelector("#generate-prompt");
    const promptDisplay = document.querySelector("#prompt-display");
    const currentVersion = document.querySelector("#current-version");
    const versionSelect = document.querySelector("#version-select");
    const copyPromptBtn = document.querySelector("#copy-prompt");
    const editPromptBtn = document.querySelector("#edit-prompt");
    const improvePromptBtn = document.querySelector("#improve-prompt");
    const testVariables = document.querySelector("#test-variables");
    const finalPromptPreview = document.querySelector("#final-prompt-preview");
    const runTestBtn = document.querySelector("#run-test");
    const testResult = document.querySelector("#test-result");
    const copyResultBtn = document.querySelector("#copy-result");

    // 新增：System/User Prompt 与生成对话框相关元素
    const systemPromptEl = document.querySelector('#system-prompt');
    const userPromptEl = document.querySelector('#user-prompt');
    const openGenBtn = document.querySelector('#open-generate-dialog');
    const toggleSystemBtn = document.querySelector('#toggle-system-prompt');
    const toggleUserBtn = document.querySelector('#toggle-user-prompt');

    const genDialog = document.querySelector('#generate-dialog');
    const dlgTask = document.querySelector('#dlg-task-description');
    const dlgVars = document.querySelector('#dlg-variables');
    const dlgStartBtn = document.querySelector('#dlg-start-generate');
    const dlgCancelBtn = document.querySelector('#dlg-cancel-generate');
    const dlgInputSection = document.querySelector('#dlg-input-section');
    const dlgPreviewSection = document.querySelector('#dlg-preview-section');
    const dlgOutput = document.querySelector('#dlg-output');
    const dlgApplyBtn = document.querySelector('#dlg-apply-system');
    const dlgSaveBtn = document.querySelector('#dlg-save-version');
    const dlgApplyWrap = document.querySelector('#dlg-apply-wrap');
    const dlgBackBtn = document.querySelector('#dlg-back-edit');
    const dlgVarsPreview = document.querySelector('#dlg-variables-preview');
    const dlgVarsTags = document.querySelector('#dlg-variables-tags');
    // 变量展示（提取后显示）
    let dlgExtractedVars = [];

    // 优化对话框元素
    const improveDialog = document.querySelector("#improve-dialog");
    const improveInstructions = document.querySelector("#improve-instructions");
    const startImproveBtn = document.querySelector("#start-improve");
    const cancelImproveBtn = document.querySelector("#cancel-improve");
    const improvementPlan = document.querySelector("#revise-plan-page");
    const improvedPrompt = document.querySelector("#revise-prompt-page");
    const improvementResultSection = document.querySelector("#improvement-result-section");
    const improveLoadingSection = document.querySelector("#improve-loading-section");

    // 项目对话框元素
    const projectDialog = document.getElementById("project-dialog");
    const projectNameInput = document.getElementById("project-name");
    const createProjectBtn = document.getElementById("create-project-btn");
    const cancelProjectBtn = document.getElementById("cancel-project-btn");
    const projectList = document.getElementById("project-list");
    const currentProjectName = document.getElementById("current-project-name");
    const newProjectBtn = document.getElementById("new-project-btn");

    // 项目操作相关元素
    const renameProjectBtn = document.getElementById("rename-project-btn");
    const deleteProjectBtn = document.getElementById("delete-project-btn");
    const renameDialog = document.getElementById("rename-dialog");
    const newProjectNameInput = document.getElementById("new-project-name");
    const confirmRenameBtn = document.getElementById("confirm-rename-btn");
    const cancelRenameBtn = document.getElementById("cancel-rename-btn");
    const deleteDialog = document.getElementById("delete-dialog");
    const confirmDeleteBtn = document.getElementById("confirm-delete-btn");
    const cancelDeleteBtn = document.getElementById("cancel-delete-btn");

    // 获取分页和返回按钮元素
    const tabImprovePlanBtn = document.querySelector("#tab-improve-plan");
    const tabImprovePromptBtn = document.querySelector("#tab-improve-prompt");
    const tabRevisePlanBtn = document.querySelector("#tab-revise-plan");
    const tabRevisePromptBtn = document.querySelector("#tab-revise-prompt");

    const improvePlanPage = document.querySelector("#improve-plan-page");
    const improvePromptPage = document.querySelector("#improve-prompt-page");
    const revisePlanPage = document.querySelector("#revise-plan-page");
    const revisePromptPage = document.querySelector("#revise-prompt-page");

    const backToInputBtn = document.querySelector("#back-to-input");
    const saveAsVersionBtn = document.querySelector("#save-as-version");
    const improveInputSection = document.querySelector("#improve-input-section");

    // 全局状态变量
    let currentPrompt = "";
    let currentPromptId = "";
    let currentProjectId = "";
    let currentVariables = [];
    let projectPrompts = []; // 存储项目所有提示词，用于版本选择

    // 临时存储优化后的提示词
    let improvedPromptContent = "";
    let improvedPromptVariables = [];

    // 基础URL
    const baseUrl = window.location.origin;

    // 新增元素引用（与 HTML 中的 ID 对应）
    const improvePlanning = document.querySelector("#improve-plan-page");
    const improvePromptContent = document.querySelector("#improve-prompt-page");

    // Apply initial reveal animations with staggered delay
    document.querySelectorAll('.prompt-section, .test-section, .top-nav').forEach((el, i) => {
        el.style.animationDelay = `${i * 40}ms`;
        el.classList.add(`reveal-1`); // Uniform base class
    });

    // 侧边栏折叠功能 - Refactored for Tailwind/CSS Transition
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function () {
            const isCollapsed = sidebar.classList.toggle('collapsed');
            sidebarToggle.setAttribute('aria-label', isCollapsed ? '展开侧边栏' : '收起侧边栏');
            const icon = sidebarToggle.querySelector('i');
            if (icon) {
                icon.className = isCollapsed ? 'ri-arrow-right-s-line text-xl' : 'ri-arrow-left-s-line text-xl';
            }
        });
    }

    console.log("DOM已加载，开始初始化应用...");

    // 初始化用户信息 - 注释掉侧边栏冗余显示，使用右上方导航栏显示
    // initUserInfo();

    // 显式调用初始化函数
    init();

    // 初始化函数
    function init() {
        console.log("正在初始化应用...");
        try {
            // 先检查用户登录状态，然后再加载数据
            checkAuthStatusBeforeInit();

            // 加载可用模型列表
            loadAvailableModels();

            // 绑定事件监听器
            attachEventListeners();

            // 清理可能遗留的旧空状态卡片，避免遮挡占位按钮
            ensureNoLegacyEmptyCard();
            // 初始化一次“生成提示词”按钮显隐
            try { updateGenerateButtonVisibility(); } catch (e) { }

            console.log("应用初始化完成");
        } catch (error) {
            console.error("应用初始化失败:", error);
            showNotification("应用初始化失败: " + error.message, "error");
        }
    }

    function ensureNoLegacyEmptyCard() {
        try {
            const emptyCards = document.querySelectorAll('.empty-prompt-view');
            emptyCards.forEach(el => el.parentNode && el.parentNode.removeChild(el));
        } catch (e) {
            // 忽略
        }
    }

    // 加载可用模型列表
    async function loadAvailableModels() {
        try {
            const response = await fetch("/api/models", {
                headers: getAuthHeaders()
            });

            if (!response.ok) {
                throw new Error("获取模型列表失败");
            }

            const data = await response.json();
            const modelSelect = document.querySelector("#model-select");

            // 清空现有选项
            modelSelect.innerHTML = "";

            // 添加新选项
            data.models.forEach(model => {
                const option = document.createElement("option");
                option.value = model.id;
                option.textContent = model.name;
                modelSelect.appendChild(option);
            });

            console.log("模型列表加载完成");
        } catch (error) {
            console.error("加载模型列表失败:", error);
            showNotification("加载模型列表失败", "error");
        }
    }

    // 检查认证状态并初始化
    async function checkAuthStatusBeforeInit() {
        try {
            console.log("检查用户认证状态...");

            // 检查是否刚刚登出
            const justLoggedOut = sessionStorage.getItem('just_logged_out') === 'true';
            if (justLoggedOut) {
                console.log("检测到刚刚登出，跳过认证检查");
                sessionStorage.removeItem('just_logged_out');
                // 如果当前不在登录页面，重定向到登录页面
                if (!window.location.pathname.includes('/auth/login-page')) {
                    window.location.href = '/auth/login-page?logout=success';
                }
                return;
            }

            // 获取用户信息
            const userInfo = await getUserInfo();

            if (userInfo) {
                console.log(`用户已登录: ${userInfo.email}，并行加载项目列表和最新提示词`);

                // 并行加载项目列表和初始最新提示词
                const [projects] = await Promise.all([
                    loadProjects(),
                    loadInitialLatest()
                ]);

                // 如果loadInitialLatest没有成功选中项目（可能失败或无最新），且有项目列表，则默认选中第一个
                if (!currentProjectId && projects && projects.length > 0) {
                    const firstProject = projects[0];
                    console.log("自动选择第一个项目:", firstProject.name);
                    await switchProject(firstProject.id, firstProject.name);
                } else if (projects && projects.length === 0) {
                    // 项目为空，显示空视图即可
                    console.log('当前没有任何项目，保持空视图');
                }
            } else {
                console.log("用户未登录，不加载项目列表");
                // 清除任何可能存在的项目数据
                document.querySelector('.empty-project-view').style.display = 'none';
                document.querySelector('.workspace-container').style.display = 'none';

                // 如果当前不在登录页面，重定向到登录页面
                if (!window.location.pathname.includes('/auth/login-page')) {
                    console.log("重定向到登录页面...");
                    window.location.href = '/auth/login-page';
                }
            }
        } catch (error) {
            console.error("检查认证状态出错:", error);
            // 出错时默认假设用户未登录
            if (!window.location.pathname.includes('/auth/login-page')) {
                window.location.href = '/auth/login-page';
            }
        }
    }

    // 首屏兜底：当无法确定当前项目且项目列表尚未能提供选择时，尝试获取“最新项目”并通过标准流程切换
    async function loadInitialLatest() {
        try {
            const resp = await fetch(`${baseUrl}/api/projects/latest`, { headers: getAuthHeaders() });
            if (!resp.ok) return;
            const data = await resp.json();
            if (!data || !data.success || !data.data) return;
            const { project } = data.data;
            if (!project) return;

            // 使用标准流程切换项目，内部会调用 loadProjectPrompts 并正确设置版本选择器
            await switchProject(project.id, project.name || '未命名项目');
            console.log('兜底：已切换到最新项目');
        } catch (e) {
            console.warn('loadInitialLatest 出错', e);
        }
    }

    // 绑定事件监听器
    function attachEventListeners() {
        // 旧的生成按钮可能不存在，保持向后兼容
        // 旧的生成提示词按钮已移除，现在使用弹窗生成
        // 新：打开“生成提示词”对话框
        if (openGenBtn) openGenBtn.addEventListener('click', showGenerateDialog);
        // 新：对话框内控制
        if (dlgStartBtn) dlgStartBtn.addEventListener('click', startGenerateInDialog);
        if (dlgCancelBtn) dlgCancelBtn.addEventListener('click', () => { hideGenerateDialog(); });
        if (dlgApplyBtn) dlgApplyBtn.addEventListener('click', applyDialogResultToSystemPrompt);
        if (dlgSaveBtn) dlgSaveBtn.addEventListener('click', saveDialogResultAsVersion);
        if (dlgBackBtn) dlgBackBtn.addEventListener('click', backToDialogEdit);

        // 新：折叠/展开控制
        if (toggleSystemBtn) toggleSystemBtn.addEventListener('click', () => toggleCollapsible('#system-prompt-container', toggleSystemBtn));
        if (toggleUserBtn) toggleUserBtn.addEventListener('click', () => toggleCollapsible('#user-prompt-container', toggleUserBtn));

        // 变量输入功能已移至生成提示词弹窗中

        if (systemPromptEl) {
            // 输入时同步 currentPrompt，并控制“生成提示词”按钮显隐与折叠状态
            systemPromptEl.addEventListener('input', () => {
                currentPrompt = systemPromptEl.value;
                updateGenerateButtonVisibility();
                autoExpandCollapsible('#system-prompt-container', systemPromptEl);
                // 延迟更新变量，避免频繁触发
                debounceUpdateVariables();
            });
            systemPromptEl.addEventListener('focus', () => expandCollapsible('#system-prompt-container'));
            systemPromptEl.addEventListener('blur', () => collapseIfEmpty('#system-prompt-container', systemPromptEl));
        }
        // User Prompt 模板输入事件监听
        if (userPromptEl) {
            userPromptEl.addEventListener('input', () => {
                // 延迟更新变量，避免频繁触发
                debounceUpdateVariables();
            });
        }

        // 版本选择下拉菜单
        if (versionSelect) {
            versionSelect.addEventListener("change", handleVersionChange);
        }

        // 复制提示词按钮
        if (copyPromptBtn) {
            copyPromptBtn.addEventListener("click", () => {
                copyToClipboard(promptDisplay.textContent);
                showNotification("提示词已复制到剪贴板", "success");
            });
        }

        // 优化提示词按钮
        if (improvePromptBtn) {
            improvePromptBtn.addEventListener("click", showImproveDialog);
        }

        // 开始优化按钮
        if (startImproveBtn) {
            startImproveBtn.addEventListener("click", handleStartImprove);
        }

        // 取消优化按钮
        if (cancelImproveBtn) {
            cancelImproveBtn.addEventListener("click", hideImproveDialog);
        }

        // 运行测试按钮
        if (runTestBtn) {
            runTestBtn.addEventListener("click", handleRunTest);
        }

        // 复制测试结果按钮
        if (copyResultBtn) {
            copyResultBtn.addEventListener("click", () => {
                copyToClipboard(testResult.textContent);
                showNotification("测试结果已复制到剪贴板", "success");
            });
        }

        // 编辑提示词按钮
        if (editPromptBtn) {
            editPromptBtn.addEventListener("click", () => {
                toggleEditMode();
            });
        }

        // 新建项目按钮
        if (newProjectBtn) {
            newProjectBtn.addEventListener("click", showProjectDialog);
        }

        // 创建项目按钮
        if (createProjectBtn) {
            createProjectBtn.addEventListener("click", handleCreateProject);
        }

        // 取消创建项目按钮
        if (cancelProjectBtn) {
            cancelProjectBtn.addEventListener("click", hideProjectDialog);
        }

        // 分页标签切换
        if (tabImprovePlanBtn && tabImprovePromptBtn && tabRevisePlanBtn && tabRevisePromptBtn) {
            tabImprovePlanBtn.addEventListener("click", () => switchImproveTab("improve-plan"));
            tabImprovePromptBtn.addEventListener("click", () => switchImproveTab("improve-prompt"));
            tabRevisePlanBtn.addEventListener("click", () => switchImproveTab("revise-plan"));
            tabRevisePromptBtn.addEventListener("click", () => switchImproveTab("revise-prompt"));
        }

        // 返回修改按钮
        if (backToInputBtn) {
            backToInputBtn.addEventListener("click", backToInput);
        }

        // 保存为优化版本按钮
        if (saveAsVersionBtn) {
            saveAsVersionBtn.addEventListener("click", saveImprovedPrompt);
        }

        // 项目重命名按钮点击事件
        if (renameProjectBtn) {
            renameProjectBtn.addEventListener("click", showRenameDialog);
        }

        // 项目删除按钮点击事件
        if (deleteProjectBtn) {
            deleteProjectBtn.addEventListener("click", showDeleteDialog);
        }

        // 重命名对话框的确认和取消按钮
        if (confirmRenameBtn) {
            confirmRenameBtn.addEventListener("click", handleRenameProject);
        }

        if (cancelRenameBtn) {
            cancelRenameBtn.addEventListener("click", hideRenameDialog);
        }

        // 删除对话框的确认和取消按钮
        if (confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener("click", handleDeleteProject);
        }

        if (cancelDeleteBtn) {
            cancelDeleteBtn.addEventListener("click", hideDeleteDialog);
        }
    }

    // renderVariableTags 函数已移除，变量输入功能已移至生成提示词弹窗中

    // ========== 折叠/展开交互 ==========
    function toggleCollapsible(containerSelector, toggleBtn) {
        const container = document.querySelector(containerSelector);
        if (!container) return;
        const collapsed = container.classList.toggle('collapsed');
        if (toggleBtn && toggleBtn.querySelector('i')) {
            toggleBtn.querySelector('i').className = collapsed ? 'ri-arrow-down-s-line' : 'ri-arrow-up-s-line';
        }
    }
    function expandCollapsible(containerSelector) {
        const container = document.querySelector(containerSelector);
        if (!container) return;
        if (container.classList.contains('collapsed')) container.classList.remove('collapsed');
    }
    function collapseIfEmpty(containerSelector, textarea) {
        const container = document.querySelector(containerSelector);
        if (!container) return;
        if (!textarea || !textarea.value.trim()) container.classList.add('collapsed');
    }
    function autoExpandCollapsible(containerSelector, textarea) {
        const container = document.querySelector(containerSelector);
        if (!container || !textarea) return;
        if (textarea.value.trim()) expandCollapsible(containerSelector);
    }

    function updateGenerateButtonVisibility() {
        if (!systemPromptEl) return;
        const btn = document.getElementById('open-generate-dialog');
        if (!btn) return;
        const hasText = !!systemPromptEl.value.trim();
        btn.style.display = hasText ? 'none' : 'inline-flex';
    }

    // ========== 生成提示词对话框 ==========
    // 流式生成完成后，优先保留前端累积的完整文本（服务端 extract_prompt 可能因
    // 未闭合的 </Instructions> 或内部 XML 子标签而截断）。
    function resolveStreamedPrompt(final, raw) {
        const serverPrompt = (final && final.prompt) ? final.prompt : '';
        const localPrompt = raw || '';
        const prompt = localPrompt.length > serverPrompt.length
            ? localPrompt
            : (serverPrompt || localPrompt);
        const variables = (final && Array.isArray(final.variables) && final.variables.length)
            ? final.variables
            : extractVariablesFromContent(prompt);
        if (final) {
            return { ...final, prompt, variables };
        }
        return { prompt, variables, version: 0, id: '' };
    }

    function showGenerateDialog() {
        if (!genDialog) return;
        // Reset dialog state
        genDialog.classList.remove('hidden');
        genDialog.classList.add('flex');
        setTimeout(() => { if (dlgTask) dlgTask.focus(); }, 150);
    }
    function hideGenerateDialog() {
        if (genDialog) {
            genDialog.classList.add('hidden');
            genDialog.classList.remove('flex');
        }
    }
    async function startGenerateInDialog() {
        if (!currentProjectId) {
            showNotification("请先选择或创建一个项目", "warning");
            return;
        }
        const task = (dlgTask?.value || '').trim();
        if (!task) {
            showNotification("请输入任务描述", "warning");
            return;
        }
        // 变量来源：只从对话框内获取
        const variablesText = (dlgVars?.value || '').trim();
        const variables = variablesText ? variablesText.split(',').map(v => v.trim()).filter(Boolean) : [];

        try {
            if (dlgPreviewSection) dlgPreviewSection.style.display = 'block';
            if (dlgInputSection) dlgInputSection.style.display = 'none';
            if (dlgOutput) {
                // 始终显示loading，直到流式的首个片段到达（由 generatePromptStreamToElement 内部切换）
                dlgOutput.innerHTML = '<div class="loading">正在生成提示词...</div>';
            }
            const { final, raw } = await generatePromptStreamToElement({
                project_id: currentProjectId,
                task: task,
                variables: variables,
                save: false // 预览模式，不落库
            }, dlgOutput);
            const result = resolveStreamedPrompt(final, raw);
            // 显示“应用到 System Prompt”
            if (dlgApplyWrap) dlgApplyWrap.style.display = 'flex';
            if (dlgApplyBtn) { dlgApplyBtn.disabled = false; dlgApplyBtn.dataset.prompt = result.prompt || ''; }
            if (dlgSaveBtn) { dlgSaveBtn.disabled = false; dlgSaveBtn.dataset.prompt = result.prompt || ''; }
            // 提取变量并渲染到外框
            dlgExtractedVars = result.variables || extractVariablesFromContent(result.prompt || '');
            renderVariablesRow(dlgExtractedVars);
            showNotification("提示词生成完成", "success");
        } catch (e) {
            console.error('生成失败:', e);
            if (dlgPreviewSection) dlgPreviewSection.style.display = 'block';
            if (dlgInputSection) dlgInputSection.style.display = 'none';
            if (dlgOutput) dlgOutput.innerHTML = '<div class="prompt-placeholder">生成失败，请重试</div>';
            if (dlgApplyWrap) dlgApplyWrap.style.display = 'none';
            if (dlgApplyBtn) dlgApplyBtn.disabled = true;
            if (dlgSaveBtn) dlgSaveBtn.disabled = true;
            showNotification("生成提示词失败: " + e.message, 'error');
        }
    }

    function backToDialogEdit() {
        if (dlgPreviewSection) dlgPreviewSection.style.display = 'none';
        if (dlgInputSection) dlgInputSection.style.display = 'block';
        // 保留输入框内容（不清空），用户可继续修改
        setTimeout(() => { if (dlgTask) dlgTask.focus(); }, 50);
    }
    function applyDialogResultToSystemPrompt() {
        console.log('applyDialogResultToSystemPrompt called');
        try {
            // 重新获取元素，确保它们存在
            const applyBtn = document.querySelector('#dlg-apply-system');

            console.log('Elements check:', {
                applyBtn: !!applyBtn,
                currentProjectId: currentProjectId,
                dlgOutput: !!dlgOutput
            });

            if (!applyBtn) {
                console.error('Missing apply button');
                showNotification('无法应用：页面元素未找到', 'error');
                return;
            }

            // 获取提示词内容（优先从 DOM 读取完整流式结果，dataset 可能不完整）
            let prompt = '';
            if (dlgOutput) {
                const pre = dlgOutput.querySelector('pre');
                prompt = pre ? pre.textContent : (dlgOutput.textContent || dlgOutput.innerText || '');
            }
            if (!prompt && applyBtn.dataset && applyBtn.dataset.prompt) {
                prompt = applyBtn.dataset.prompt;
            }

            if (!prompt || !currentProjectId) {
                console.error('Missing data:', { promptLength: prompt.length, currentProjectId });
                showNotification('无法应用：缺少内容或项目未选中', 'error');
                return;
            }

            console.log('Starting apply process...');

            // UI 反馈
            applyBtn.disabled = true;
            const oldHtml = applyBtn.innerHTML;
            applyBtn.innerHTML = '<i class="ri-loader-4-line" style="animation: spin 1s linear infinite;"></i> 应用中...';

            // 保存为新版本
            const saveData = {
                project_id: currentProjectId,
                system_prompt: prompt,
                user_prompt: '',
                name: `应用版 ${new Date().toLocaleString('zh-CN')}`,
                variables: dlgExtractedVars || []
            };

            console.log('Saving data:', saveData);

            fetch(`${baseUrl}/api/prompts`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
                body: JSON.stringify(saveData)
            }).then(async resp => {
                console.log('Save response:', resp.status, resp.statusText);
                if (!resp.ok) {
                    const errorText = await resp.text();
                    console.error('Save failed:', errorText);
                    throw new Error(errorText);
                }
                const result = await resp.json();
                console.log('Save successful:', result);

                // 更新当前提示词内容和显示
                currentPrompt = prompt;
                updateGenerateButtonVisibility();

                // 重新加载项目提示词列表，这会自动刷新左侧显示
                await loadProjectPrompts(currentProjectId);
                showNotification('已应用并保存为新版本', 'success');
                hideGenerateDialog();
            }).catch(err => {
                console.error('应用保存失败:', err);
                showNotification('保存失败：' + (err && err.message ? err.message : ''), 'error');
                hideGenerateDialog();
            }).finally(() => {
                applyBtn.disabled = false;
                applyBtn.innerHTML = oldHtml;
                console.log('Apply process completed');
            });
        } catch (err) {
            console.error('applyDialogResultToSystemPrompt error:', err);
            showNotification('应用失败：' + (err && err.message ? err.message : ''), 'error');
        }
    }

    function injectVariablesPreview(container, vars) {
        // 兼容旧逻辑（不再使用在内容区内部显示）
        renderVariablesRow(vars);
    }

    function renderVariablesRow(vars) {
        if (!dlgVarsPreview || !dlgVarsTags) return;
        const list = (vars || []).map(v => `<span class="variable-tag">${escapeHtml(v)}</span>`).join(' ');
        dlgVarsTags.innerHTML = list || '<span class="prompt-placeholder">无变量</span>';
        dlgVarsPreview.style.display = 'block';
    }

    async function saveDialogResultAsVersion() {
        if (!dlgSaveBtn || !currentProjectId) return;
        let prompt = '';
        if (dlgOutput) {
            const pre = dlgOutput.querySelector('pre');
            prompt = pre ? pre.textContent : (dlgOutput.textContent || '');
        }
        if (!prompt) prompt = dlgSaveBtn.dataset.prompt || '';
        if (!prompt) {
            showNotification('没有可保存的内容', 'warning');
            return;
        }
        try {
            dlgSaveBtn.disabled = true;
            dlgSaveBtn.textContent = '保存中...';
            const resp = await fetch(`${baseUrl}/api/prompts`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
                body: JSON.stringify({
                    project_id: currentProjectId,
                    system_prompt: prompt,
                    user_prompt: '',
                    name: `生成版 ${new Date().toLocaleString('zh-CN')}`,
                    variables: dlgExtractedVars || []
                })
            });
            if (!resp.ok) {
                const t = await resp.text();
                throw new Error(t || '保存失败');
            }
            const data = await resp.json();
            // 更新版本列表与当前显示
            await loadProjectPrompts(currentProjectId);
            currentPrompt = prompt;
            if (promptDisplay) promptDisplay.innerHTML = `<pre>${escapeHtml(prompt)}</pre>`;
            showNotification('已保存为新版本', 'success');
        } catch (e) {
            console.error('保存失败:', e);
            showNotification('保存失败: ' + e.message, 'error');
        } finally {
            dlgSaveBtn.textContent = '保存为版本';
            dlgSaveBtn.disabled = false;
        }
    }

    // 优化对话框标签切换
    function switchImproveTab(tabName) {
        console.log(`切换到标签: ${tabName}`);

        // 更新所有标签按钮状态
        const allTabs = ["improve-plan", "improve-prompt", "revise-plan", "revise-prompt"];

        allTabs.forEach(tab => {
            const tabElement = document.getElementById(`${tab}-tab`);
            if (tabElement) {
                const isActive = tab === tabName;
                tabElement.classList.toggle("active", isActive);
                // Transitions handled by CSS .tab-button.active
            }
        });

        // 更新页面显示
        const improvePlanPage = document.getElementById("improve-plan-page");
        const improvePromptPage = document.getElementById("improve-prompt-page");
        const revisePlanPage = document.getElementById("revise-plan-page");
        const revisePromptPage = document.getElementById("revise-prompt-page");

        if (improvePlanPage) improvePlanPage.style.display = tabName === "improve-plan" ? "block" : "none";
        if (improvePromptPage) improvePromptPage.style.display = tabName === "improve-prompt" ? "block" : "none";
        if (revisePlanPage) revisePlanPage.style.display = tabName === "revise-plan" ? "block" : "none";
        if (revisePromptPage) revisePromptPage.style.display = tabName === "revise-prompt" ? "block" : "none";

        console.log(`标签切换完成: ${tabName}`);
    }

    // 显示优化对话框
    function showImproveDialog() {
        if (!currentPrompt) {
            showNotification("请先生成或选择一个提示词", "warning");
            return;
        }

        // 重置对话框内容
        improveInstructions.value = "";
        improvementResultSection.classList.add("hidden");
        improveInputSection.classList.remove("hidden");
        improveLoadingSection.classList.add("hidden");

        // 重置优化结果
        improvePlanning.innerHTML = "";
        improvePromptContent.innerHTML = "";
        improvementPlan.innerHTML = "";
        improvedPrompt.innerHTML = "";
        improvedPromptContent = "";
        improvedPromptVariables = [];

        // 重置标签页状态
        switchImproveTab("improve-plan");

        // 显示对话框
        improveDialog.classList.remove("hidden");
        improveDialog.classList.add("flex");
        improveInstructions.focus();
    }

    // 隐藏优化对话框
    function hideImproveDialog() {
        improveDialog.classList.add("hidden");
        improveDialog.classList.remove("flex");
    }

    // 返回到输入界面
    function backToInput() {
        // 隐藏结果区域，显示输入区域
        improvementResultSection.classList.add("hidden");
        improveInputSection.classList.remove("hidden");
        improveLoadingSection.classList.add("hidden");

        // 重置输入
        improveInstructions.value = "";
        improveInstructions.focus();
    }

    // 处理版本选择变更
    async function handleVersionChange(event) {
        const versionId = event.target.value;
        if (!versionId) return;

        try {
            // 显示加载状态
            promptDisplay.innerHTML = '<div class="loading">正在加载版本内容...</div>';

            // 从API获取特定版本的提示词内容
            const response = await fetch(`${baseUrl}/api/projects/${currentProjectId}/prompts/${versionId}`, {
                headers: {
                    ...getAuthHeaders()
                },
                credentials: 'include'
            });

            // 特殊处理404错误
            if (response.status === 404) {
                console.error("提示词版本不存在或已被删除");
                showNotification("提示词版本不存在或已被删除", "error");
                promptDisplay.innerHTML = '<div class="error">提示词版本不存在或已被删除</div>';

                // 重新加载项目提示词列表以更新版本选择器
                await loadProjectPrompts(currentProjectId);
                return;
            }

            if (!response.ok) {
                throw new Error(`获取版本内容失败: HTTP ${response.status}`);
            }

            const result = await response.json();
            if (!result.success) {
                throw new Error(result.message || "获取版本内容失败");
            }

            // 获取版本内容（支持 system_prompt 和 user_prompt）
            const version = result.data;
            if (version) {
                displayPrompt(
                    version.system_prompt || version.content,
                    version.id,
                    version.version,
                    version.variables,
                    version.user_prompt || ''
                );
            } else {
                throw new Error("未找到版本内容");
            }

        } catch (error) {
            console.error("加载版本内容失败:", error);
            showNotification("加载版本内容失败: " + error.message, "error");
            promptDisplay.innerHTML = '<div class="error">加载版本内容失败</div>';
        }
    }

    // 显示项目创建对话框
    function showProjectDialog() {
        // 设置默认项目名称
        const now = new Date();
        const defaultName = `新项目 ${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
        projectNameInput.value = defaultName;

        // 显示对话框并设置样式
        projectDialog.classList.remove('hidden');
        projectDialog.classList.add('flex');

        // 聚焦到输入框，全选文本内容方便用户修改
        setTimeout(() => {
            projectNameInput.focus();
            projectNameInput.select();
        }, 100);
    }

    // 隐藏项目创建对话框
    function hideProjectDialog() {
        projectDialog.classList.add('hidden');
        projectDialog.classList.remove('flex');
        projectNameInput.value = "";
    }

    // 处理创建项目
    async function handleCreateProject() {
        const projectName = projectNameInput.value.trim();

        if (!projectName) {
            showNotification("请输入项目名称", "warning");
            return;
        }

        try {
            // 显示加载状态
            createProjectBtn.disabled = true;
            createProjectBtn.textContent = "创建中...";

            console.log(`尝试创建项目: ${projectName}`);

            const response = await fetch(`${baseUrl}/api/projects`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...getAuthHeaders()
                },
                credentials: 'include',
                body: JSON.stringify({
                    name: projectName
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error("创建项目HTTP错误:", response.status, errorData);
                throw new Error(errorData.detail || errorData.message || "创建项目失败");
            }

            const result = await response.json();
            console.log("创建项目响应:", result);

            // 检查响应格式，获取项目数据
            if (!result.success) {
                throw new Error(result.message || "创建项目失败");
            }

            // 获取项目数据（在data字段中）
            const newProject = result.data;
            if (!newProject || !newProject.id) {
                console.error("创建项目成功但返回的数据格式不正确:", result);
                throw new Error("服务器返回的项目数据格式不正确");
            }

            console.log("项目创建成功:", newProject);

            // 隐藏对话框
            hideProjectDialog();

            // 重新加载项目列表
            console.log("重新加载项目列表...");
            try {
                const projects = await loadProjects();
                console.log("项目列表加载完成，获取到项目数量:", projects ? projects.length : 0);

                // 等待一小段时间确保项目列表已更新
                setTimeout(() => {
                    // 确保projects是数组
                    if (!Array.isArray(projects)) {
                        console.error("加载的项目列表不是数组:", projects);
                        return;
                    }

                    // 检查新项目是否在列表中
                    const projectExists = projects.some(p => p.id === newProject.id);
                    console.log(`新项目${projectExists ? '存在' : '不存在'}于加载的项目列表中`);

                    // 切换到新项目
                    console.log(`切换到新创建的项目: ID=${newProject.id}, 名称=${newProject.name}`);
                    switchProject(newProject.id, newProject.name);

                    // 显示成功通知
                    showNotification(result.message || "项目创建成功", "success");
                }, 500);
            } catch (loadError) {
                console.error("重新加载项目列表失败:", loadError);
                // 即使项目列表加载失败，仍然尝试切换到新项目
                switchProject(newProject.id, newProject.name);
                showNotification("项目创建成功，但项目列表更新失败", "warning");
            }
        } catch (error) {
            console.error("创建项目失败:", error);
            showNotification("创建项目失败: " + error.message, "error");
        } finally {
            // 恢复按钮状态
            createProjectBtn.disabled = false;
            createProjectBtn.textContent = "创建项目";
        }
    }

    // 加载项目列表
    async function loadProjects() {
        try {
            console.log("开始加载项目列表...");

            const response = await fetch(`${baseUrl}/api/projects`, {
                headers: getAuthHeaders()
            });

            if (!response.ok) {
                throw new Error('加载项目失败');
            }

            const result = await response.json();

            // 检查响应格式
            if (!result.success) {
                throw new Error(result.message || "获取项目列表失败");
            }

            // 获取项目列表（在data字段中）
            const projects = result.data || [];
            console.log(`加载了 ${projects.length} 个项目`);

            // 清空项目列表
            projectList.innerHTML = '';

            // 显示/隐藏相应的视图
            const emptyProjectView = document.querySelector('.empty-project-view');
            const workspaceContainer = document.querySelector('.workspace-container');

            if (projects.length === 0) {
                console.log("未找到项目，显示空项目视图");
                if (emptyProjectView) {
                    emptyProjectView.classList.remove('hidden');
                    emptyProjectView.classList.add('flex');
                }
                if (workspaceContainer) {
                    workspaceContainer.classList.add('hidden');
                    workspaceContainer.classList.remove('flex');
                }
                projectList.innerHTML = '<div class="no-projects">暂无项目</div>';
                return [];
            } else {
                console.log("找到项目，显示工作区");
                if (emptyProjectView) {
                    emptyProjectView.classList.add('hidden');
                    emptyProjectView.classList.remove('flex');
                }
                if (workspaceContainer) {
                    workspaceContainer.classList.remove('hidden');
                    workspaceContainer.classList.add('flex');
                }
            }

            projects.forEach(project => {
                const isActive = project.id === currentProjectId;
                const projectItem = document.createElement('div');
                projectItem.className = `project-item group flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-200 ${isActive ? 'bg-[var(--bg-main)] shadow-sm text-[var(--accent-primary)] font-bold' : 'text-[var(--text-secondary)] hover:bg-[var(--bg-main)]/50'}`;
                projectItem.dataset.projectId = project.id;
                projectItem.innerHTML = `
                    <div class="flex items-center gap-2.5 flex-1 min-w-0">
                        <i class="ri-folder-3-line ${isActive ? 'text-[var(--accent-primary)]' : 'text-[var(--text-dim)]'} transition-colors"></i>
                        <span class="project-name text-xs truncate">${escapeHtml(project.name)}</span>
                    </div>
                    <div class="project-actions flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                        <button class="p-1 hover:text-white transition-colors edit-project" aria-label="重命名项目 ${escapeHtml(project.name)}">
                            <i class="ri-edit-line text-sm"></i>
                        </button>
                        <button class="p-1 hover:text-rose-400 transition-colors delete-project" aria-label="删除项目 ${escapeHtml(project.name)}">
                            <i class="ri-delete-bin-line text-sm"></i>
                        </button>
                    </div>
                `;

                projectList.appendChild(projectItem);

                // 添加点击事件
                projectItem.addEventListener('click', (e) => {
                    if (!e.target.closest('.project-actions')) {
                        switchProject(project.id, project.name);
                    }
                });

                // 添加编辑和删除按钮事件
                const editBtn = projectItem.querySelector('.edit-project');
                const deleteBtn = projectItem.querySelector('.delete-project');

                editBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    currentProjectId = project.id;
                    showRenameDialog();
                });

                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    currentProjectId = project.id;
                    showDeleteDialog();
                });
            });

            // 自动选择逻辑已移至checkAuthStatusBeforeInit，以支持并行加载

            return projects;

        } catch (error) {
            console.error('加载项目失败:', error);
            showNotification('加载项目失败: ' + error.message, 'error');
            return [];
        }
    }

    // 调试项目列表状态
    function debugProjects() {
        console.log("=== 项目列表状态调试 ===");
        console.log("当前项目ID:", currentProjectId);
        console.log("当前项目名称:", currentProjectName.textContent);
        console.log("项目DOM元素数量:", projectList.querySelectorAll(".project-item").length);

        // 检查项目元素活动状态
        const activeProjects = projectList.querySelectorAll(".project-item.active");
        console.log("活动状态的项目数量:", activeProjects.length);

        if (activeProjects.length > 0) {
            console.log("活动项目ID:", activeProjects[0].dataset.id);
        }

        // 检查空项目视图状态
        const emptyView = document.querySelector(".empty-project-view");
        if (emptyView) {
            console.log("空项目视图显示状态:", emptyView.classList.contains('hidden') ? 'hidden' : 'visible');
        } else {
            console.log("未找到空项目视图元素");
        }
        console.log("=== 调试结束 ===");
    }

    // 切换项目
    async function switchProject(projectId, projectName) {
        if (!projectId || !projectName) {
            console.error("切换项目失败：无效的项目ID或名称", { projectId, projectName });
            return;
        }

        if (currentProjectId === projectId) {
            console.log("已经选中该项目，无需切换");
            return;
        }

        console.log(`切换到项目: ID=${projectId}, 名称=${projectName}`);

        // 更新当前项目
        currentProjectId = projectId;
        if (currentProjectName) {
            currentProjectName.textContent = projectName;
        }

        // 显示项目操作按钮
        toggleProjectActions(true);

        // 高亮选中的项目
        const projectItems = projectList.querySelectorAll(".project-item");
        projectItems.forEach(item => {
            const icon = item.querySelector('i');
            const isActive = item.dataset.projectId === projectId;

            if (isActive) {
                item.classList.add("bg-[var(--bg-main)]", "shadow-sm", "text-[var(--accent-primary)]", "font-bold", "active");
                if (icon) {
                    icon.classList.remove("text-[var(--text-dim)]");
                    icon.classList.add("text-[var(--accent-primary)]");
                }
            } else {
                item.classList.remove("bg-[var(--bg-main)]", "shadow-sm", "text-[var(--accent-primary)]", "font-bold", "active");
                if (icon) {
                    icon.classList.remove("text-[var(--accent-primary)]");
                    icon.classList.add("text-[var(--text-dim)]");
                }
            }
        });

        try {
            // 显示加载状态
            if (promptDisplay) {
                promptDisplay.innerHTML = '<div class="loading-pulse">正在加载项目提示词...</div>';
            }

            // 加载项目的提示词
            await loadProjectPrompts(projectId);

        } catch (error) {
            console.error("切换项目失败:", error);
            showNotification("加载项目提示词失败: " + error.message, "error");

            // 重置提示词显示区域
            resetPromptDisplay();
        }
    }

    // 切换项目操作按钮显示状态
    function toggleProjectActions(show) {
        const projectActions = document.querySelectorAll('.project-action-btn');
        projectActions.forEach(btn => {
            btn.classList.toggle('inline-block', show);
            btn.classList.toggle('hidden', !show);
        });
    }

    // 加载项目提示词
    async function loadProjectPrompts(projectId) {
        try {
            console.log(`开始加载项目 ${projectId} 的提示词...`);

            const response = await fetch(`${baseUrl}/api/projects/${projectId}/prompts`, {
                headers: getAuthHeaders()
            });

            if (!response.ok) {
                throw new Error('加载提示词失败');
            }

            const result = await response.json();

            // 检查响应格式
            if (!result.success) {
                throw new Error(result.message || "获取提示词列表失败");
            }

            // 获取提示词列表（在data字段中）
            const prompts = result.data || [];
            console.log(`获取到 ${prompts.length} 个提示词版本`);

            // 保存到全局变量
            projectPrompts = prompts;

            if (prompts.length > 0) {
                console.log("找到提示词，显示第一个版本");
                // 更新版本选择器
                updateVersionSelector(prompts);

                // 自动选择第一个提示词版本
                // 先请求最新一版，快速渲染首屏
                try {
                    const latestResp = await fetch(`${baseUrl}/api/projects/${projectId}/prompts/latest`, { headers: getAuthHeaders() });
                    if (latestResp.ok) {
                        const latestData = await latestResp.json();
                        if (latestData && latestData.success && latestData.data) {
                            const lp = latestData.data;
                            let promptVariables = lp.variables || [];
                            if (!promptVariables || promptVariables.length === 0) {
                                promptVariables = extractVariablesFromContent(lp.system_prompt || lp.content);
                            }
                            // 使用新的格式：支持 system_prompt 和 user_prompt
                            displayPrompt(
                                lp.system_prompt || lp.content,
                                lp.id,
                                lp.version,
                                promptVariables,
                                lp.user_prompt || ''
                            );
                            currentPromptId = lp.id;
                            currentPrompt = lp.system_prompt || lp.content;
                            currentVariables = promptVariables;
                            updateTestArea(promptVariables);
                        }
                    }
                } catch (e) {
                    console.warn('获取最新一版失败，回退到本地列表首项', e);
                    const firstPrompt = prompts[0];
                    let promptVariables = firstPrompt.variables || extractVariablesFromContent(firstPrompt.system_prompt || firstPrompt.content);
                    // 使用新的格式
                    displayPrompt(
                        firstPrompt.system_prompt || firstPrompt.content,
                        firstPrompt.id,
                        firstPrompt.version,
                        promptVariables,
                        firstPrompt.user_prompt || ''
                    );
                    currentPromptId = firstPrompt.id;
                    currentPrompt = firstPrompt.system_prompt || firstPrompt.content;
                    currentVariables = promptVariables;
                    updateTestArea(promptVariables);
                }

                // 重新赋值项目提示词列表
                projectPrompts = prompts;

                // 更新测试区域
                // updateTestArea(promptVariables);
            } else {
                console.log("未找到提示词，显示空提示词视图");
                showEmptyPromptView();
            }

        } catch (error) {
            console.error('加载提示词失败:', error);
            showNotification('加载提示词失败: ' + error.message, 'error');
            showEmptyPromptView();
        }
    }

    // 显示空提示词状态：仅显示占位区与“生成提示词”按钮，移除旧的空视图卡片
    function showEmptyPromptView() {
        // 重置当前提示词状态
        currentPrompt = "";
        currentPromptId = "";
        currentVariables = [];

        // 版本标记
        currentVersion.textContent = "未生成";

        // 移除 loading
        const loadingElement = promptDisplay.querySelector('.loading-pulse');
        if (loadingElement) loadingElement.remove();

        // 移除（或隐藏）旧的 empty-prompt-view，避免与占位区重复
        const oldEmpty = promptDisplay.querySelector('.empty-prompt-view');
        if (oldEmpty) {
            oldEmpty.classList.add('hidden');
            oldEmpty.classList.remove('flex');
        }

        // 确保占位区存在且可见；若不存在则创建带按钮的占位区
        let placeholder = promptDisplay.querySelector('.prompt-placeholder');
        if (!placeholder) {
            promptDisplay.innerHTML = `
                <div class="prompt-placeholder">
                    点击按钮生成你的第一个 System Prompt
                    <div style="margin-top:8px;">
                        <button id="open-generate-dialog" class="btn btn-primary"><i class="ri-wand-2-line"></i> 生成提示词</button>
                    </div>
                </div>
            `;
            placeholder = promptDisplay.querySelector('.prompt-placeholder');
        } else {
            placeholder.classList.remove('hidden');
        }
        promptDisplay.classList.remove('has-content');

        // 绑定按钮
        const cta = document.getElementById('open-generate-dialog');
        if (cta && !cta.dataset.bound) {
            cta.addEventListener('click', showGenerateDialog);
            cta.dataset.bound = '1';
        }

        // 测试区初始化
        updateTestArea([]);
        versionSelect.selectedIndex = 0;
    }

    // 重置提示词显示区域
    function resetPromptDisplay() {
        currentPrompt = "";
        currentPromptId = "";
        currentVariables = [];

        currentVersion.textContent = "未生成";

        // 清除所有内容并设置包含按钮的占位区
        promptDisplay.innerHTML = `
            <div class="prompt-placeholder">
                点击按钮生成你的第一个 System Prompt
                <div style="margin-top:8px;">
                    <button id="open-generate-dialog" class="btn btn-primary"><i class="ri-wand-2-line"></i> 生成提示词</button>
                </div>
            </div>
         `;
        promptDisplay.classList.remove('has-content');

        // 绑定按钮
        const cta = document.getElementById('open-generate-dialog');
        if (cta && !cta.dataset.bound) {
            cta.addEventListener('click', showGenerateDialog);
            cta.dataset.bound = '1';
        }

        // 重置测试区域
        updateTestArea([]);

        // 重置版本选择
        versionSelect.selectedIndex = 0;
    }

    // 更新版本选择下拉菜单
    function updateVersionSelector(prompts) {
        console.log("更新版本选择器，提示词数量:", prompts.length);

        // 记住当前选中的值
        const currentSelectedId = versionSelect.value;

        // 清空选择器
        versionSelect.innerHTML = '';

        // 检查prompts是否为有效数组
        if (!Array.isArray(prompts)) {
            console.warn("更新版本选择器: 提示词不是有效数组", prompts);
            const emptyOption = document.createElement("option");
            emptyOption.value = "";
            emptyOption.textContent = "暂无历史版本";
            emptyOption.disabled = true;
            versionSelect.appendChild(emptyOption);
            versionSelect.disabled = true;
            return;
        }

        // 启用选择器
        versionSelect.disabled = false;

        // 添加默认选项
        const defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.textContent = prompts.length > 0 ? "选择历史版本" : "暂无历史版本";
        versionSelect.appendChild(defaultOption);

        if (prompts.length === 0) {
            // 如果没有版本，禁用选择器
            versionSelect.disabled = true;
            return;
        }

        console.log(`添加 ${prompts.length} 个版本选项`);

        // 添加提示词版本到选择器
        prompts.forEach(prompt => {
            const option = document.createElement("option");
            option.value = prompt.id;
            option.textContent = `版本 ${prompt.version || '未知'} (${formatDate(prompt.created_at)})`;
            versionSelect.appendChild(option);
            console.log(`添加版本选项: ${option.textContent}`);
        });

        // 如果之前有选中的值，尝试恢复选中状态
        if (currentSelectedId) {
            const option = Array.from(versionSelect.options).find(opt => opt.value === currentSelectedId);
            if (option) {
                versionSelect.value = currentSelectedId;
                console.log(`恢复之前选中的版本: ${option.textContent}`);
                return;
            }
        }

        // 如果当前显示了某个提示词，自动选中对应的版本
        if (currentPromptId) {
            const option = Array.from(versionSelect.options).find(opt => opt.value === currentPromptId);
            if (option) {
                versionSelect.value = currentPromptId;
                console.log(`自动选中当前显示的版本: ${option.textContent}`);
            }
        }
    }

    // 格式化日期
    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString("zh-CN", {
            year: "numeric",
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit"
        });
    }

    // 显示提示词（支持 system_prompt 和 user_prompt）
    function displayPrompt(content, id, version, variables, userPrompt) {
        // 如果第一个参数是对象（完整的 prompt 对象），解构它
        if (typeof content === 'object' && content !== null && content.id) {
            const promptObj = content;
            content = promptObj.system_prompt || promptObj.content || '';
            id = promptObj.id;
            version = promptObj.version;
            variables = promptObj.variables || [];
            userPrompt = promptObj.user_prompt || '';
        }

        console.log("displayPrompt 函数被调用，参数:", {
            system_prompt: content ? content.substring(0, 50) + "..." : "空",
            user_prompt: userPrompt ? userPrompt.substring(0, 50) + "..." : "空",
            id,
            version,
            variables: JSON.stringify(variables)
        });

        currentPrompt = content;
        currentPromptId = id;  // 直接使用 id
        currentVariables = variables || [];

        // 更新版本显示
        currentVersion.textContent = `v${version}`;

        // 隐藏空提示词视图，显示实际内容
        const emptyPromptView = promptDisplay.querySelector(".empty-prompt-view");
        if (emptyPromptView) {
            emptyPromptView.classList.add("hidden");
            emptyPromptView.classList.remove("flex");
        }

        // 更新 System Prompt 显示
        promptDisplay.innerHTML = `<pre>${escapeHtml(content)}</pre>`;
        promptDisplay.classList.add('has-content');

        // 更新 User Prompt 模板（如果有保存的 user_prompt）
        if (userPromptEl && userPrompt) {
            userPromptEl.value = userPrompt;
        }

        // 更新测试区域，从 System Prompt 和 User Prompt 模板中提取变量
        updateVariablesFromBothPrompts();

        // 同步版本选择器的选中值
        if (versionSelect) {
            console.log(`设置版本选择器选中值为: ${id}`);
            // 查找对应的选项
            const option = Array.from(versionSelect.options).find(opt => opt.value === id);
            if (option) {
                versionSelect.value = id;
                console.log(`已选中版本: ${option.textContent}`);
            } else {
                console.warn(`未找到对应的版本选项: ${id}`);
                versionSelect.selectedIndex = 0;
            }
        }
    }

    // 从提示词内容中提取变量
    function extractVariablesFromContent(content) {
        if (!content) return [];

        const variables = [];

        try {
            // 提取所有格式的变量
            // 1. ${VARIABLE} 格式 (美元符号在外)
            const dollarBraceMatches = content.match(/\$\{([\u4e00-\u9fa5A-Za-z0-9_]+)\}/g) || [];
            dollarBraceMatches.forEach(match => {
                const varName = match.substring(2, match.length - 1);
                if (!variables.includes(varName)) {
                    variables.push(varName);
                }
            });

            // 2. {$VARIABLE} 格式 (美元符号在内)
            const braceDollarMatches = content.match(/\{\$([\u4e00-\u9fa5A-Za-z0-9_]+)\}/g) || [];
            braceDollarMatches.forEach(match => {
                const varName = match.substring(2, match.length - 1);
                if (!variables.includes(varName)) {
                    variables.push(varName);
                }
            });

            // 3. {{VARIABLE}} 格式 (双大括号)
            const doubleBraceMatches = content.match(/\{\{([\u4e00-\u9fa5A-Za-z0-9_]+)\}\}/g) || [];
            doubleBraceMatches.forEach(match => {
                const varName = match.substring(2, match.length - 2);
                if (!variables.includes(varName)) {
                    variables.push(varName);
                }
            });

        } catch (e) {
            console.error("提取变量时发生错误:", e);
        }

        console.log("提取的变量结果:", variables);
        return variables;
    }

    // 从 System Prompt 和 User Prompt 模板中提取并合并变量
    function updateVariablesFromBothPrompts() {
        // 获取 System Prompt 内容
        const systemContent = systemPromptEl ? systemPromptEl.value : (currentPrompt || '');
        // 获取 User Prompt 模板内容
        const userContent = userPromptEl ? userPromptEl.value : '';
        
        // 分别提取变量
        const systemVars = extractVariablesFromContent(systemContent);
        const userVars = extractVariablesFromContent(userContent);
        
        // 合并去重
        const allVariables = [...new Set([...systemVars, ...userVars])];
        
        console.log("从 System Prompt 提取的变量:", systemVars);
        console.log("从 User Prompt 模板提取的变量:", userVars);
        console.log("合并后的变量:", allVariables);
        
        // 更新测试区域
        updateTestArea(allVariables);
    }

    // 更新测试区域
    // 防抖定时器
    let updateVariablesTimer = null;
    
    // 防抖更新变量（避免输入时频繁触发）
    function debounceUpdateVariables() {
        if (updateVariablesTimer) {
            clearTimeout(updateVariablesTimer);
        }
        updateVariablesTimer = setTimeout(() => {
            updateVariablesFromBothPrompts();
        }, 500); // 500ms 延迟
    }
    
    // 存储变量值（支持文本+图片）: { "VAR1": {text: "", images: []}, ... }
    let variableValuesWithMedia = {};

    function updateTestArea(variables) {
        // 清空测试变量区域
        testVariables.innerHTML = "";
        
        // 保留旧的变量值
        const oldValues = { ...variableValuesWithMedia };
        
        // 重置变量值存储，但保留已有值
        variableValuesWithMedia = {};

        // 如果没有变量，显示提示信息
        if (!variables || variables.length === 0) {
            testVariables.innerHTML = '<div class="text-slate-500 text-sm italic py-4">当前提示词没有定义变量</div>';
            return;
        }

        // 为每个变量创建输入框（支持文本+图片）
        variables.forEach(variable => {
            // 保留已有的变量值，否则初始化
            if (oldValues[variable]) {
                variableValuesWithMedia[variable] = oldValues[variable];
            } else {
                variableValuesWithMedia[variable] = { text: "", images: [] };
            }
            
            const existingValue = variableValuesWithMedia[variable];
            const hasImages = existingValue.images && existingValue.images.length > 0;
            
            const variableRow = document.createElement("div");
            variableRow.className = "variable-row group bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg p-3 mb-3";
            variableRow.innerHTML = `
                <div class="flex items-center justify-between mb-2">
                    <div class="text-[10px] font-bold uppercase tracking-widest text-[var(--accent-primary)]">\${${variable}}</div>
                    <label class="cursor-pointer text-[var(--text-dim)] hover:text-[var(--accent-primary)] transition-colors flex items-center gap-1 text-xs">
                        <i class="ri-image-add-line"></i>
                        <span>添加图片</span>
                        <input type="file" class="variable-image-input hidden" accept="image/*" multiple data-var="${variable}">
                    </label>
                </div>
                <textarea class="w-full bg-white border border-[var(--border-subtle)] rounded-lg px-3 py-2 text-sm text-[var(--text-secondary)] focus:border-[var(--accent-primary)] focus:ring-2 focus:ring-[var(--accent-primary)]/5 outline-none transition-all variable-input placeholder:text-[var(--text-dim)]/40 shadow-sm resize-none" 
                    data-var="${variable}" 
                    rows="2"
                    placeholder="输入 ${variable} 的文本内容...">${escapeHtml(existingValue.text || '')}</textarea>
                <div class="variable-images-preview ${hasImages ? '' : 'hidden'} mt-2 flex flex-wrap gap-2" data-var="${variable}"></div>
            `;

            testVariables.appendChild(variableRow);
            
            // 如果有图片，渲染图片预览
            if (hasImages) {
                renderVariableImages(variable);
            }
        });
        
        // 绑定事件
        bindVariableEvents();
    }
    
    // 绑定变量输入事件
    function bindVariableEvents() {
        // 文本输入事件
        document.querySelectorAll('.variable-input').forEach(input => {
            input.addEventListener('input', (e) => {
                const varName = e.target.dataset.var;
                if (variableValuesWithMedia[varName]) {
                    variableValuesWithMedia[varName].text = e.target.value;
                }
            });
        });
        
        // 图片上传事件
        document.querySelectorAll('.variable-image-input').forEach(input => {
            input.addEventListener('change', async (e) => {
                const varName = e.target.dataset.var;
                const files = e.target.files;
                if (!files || files.length === 0) return;
                
                for (const file of files) {
                    if (!file.type.startsWith('image/')) {
                        showNotification("只支持图片文件", "warning");
                        continue;
                    }
                    if (file.size > 10 * 1024 * 1024) {
                        showNotification(`图片 ${file.name} 超过 10MB 限制`, "warning");
                        continue;
                    }
                    try {
                        const base64 = await fileToBase64(file);
                        if (variableValuesWithMedia[varName]) {
                            variableValuesWithMedia[varName].images.push(base64);
                        }
                    } catch (error) {
                        console.error("图片转换失败:", error);
                        showNotification("图片处理失败", "error");
                    }
                }
                renderVariableImages(varName);
                e.target.value = '';
            });
        });
    }
    
    // 渲染变量的图片预览
    function renderVariableImages(varName) {
        const previewEl = document.querySelector(`.variable-images-preview[data-var="${varName}"]`);
        if (!previewEl || !variableValuesWithMedia[varName]) return;
        
        const images = variableValuesWithMedia[varName].images;
        if (images.length === 0) {
            previewEl.classList.add('hidden');
            previewEl.innerHTML = '';
            return;
        }
        
        previewEl.classList.remove('hidden');
        previewEl.innerHTML = images.map((base64, imgIndex) => `
            <div class="relative group">
                <img src="${base64}" alt="图片" class="w-14 h-14 object-cover rounded-lg border border-[var(--border-subtle)]">
                <button type="button" class="remove-var-image absolute -top-1.5 -right-1.5 w-5 h-5 bg-red-500 text-white rounded-full text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    data-var="${varName}" data-img-index="${imgIndex}">
                    <i class="ri-close-line"></i>
                </button>
            </div>
        `).join('');
        
        // 绑定删除图片事件
        previewEl.querySelectorAll('.remove-var-image').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const vName = e.currentTarget.dataset.var;
                const imgIdx = parseInt(e.currentTarget.dataset.imgIndex);
                if (variableValuesWithMedia[vName]) {
                    variableValuesWithMedia[vName].images.splice(imgIdx, 1);
                    renderVariableImages(vName);
                }
            });
        });
    }

    // 已默认流式，移除开关

    // 解析SSE片段，返回 {delta, done, payload}
    function parseSSEChunk(buffer) {
        const lines = buffer.split(/\n/);
        const events = [];
        let currentEvent = { type: 'message', data: [] };

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line === '') {
                // 空行表示事件结束，处理当前事件
                if (currentEvent.data.length) {
                    const dataStr = currentEvent.data.join('\n');
                    if (currentEvent.type === 'done') {
                        try {
                            events.push({ done: true, payload: JSON.parse(dataStr) });
                        } catch {
                            events.push({ done: true, payload: null });
                        }
                    } else {
                        try {
                            const obj = JSON.parse(dataStr);
                            if (obj && typeof obj.delta === 'string') {
                                events.push({ delta: obj.delta });
                            }
                        } catch (_) {
                            events.push({ delta: dataStr });
                        }
                    }
                }
                currentEvent = { type: 'message', data: [] };
                continue;
            }
            if (line.startsWith('event:')) {
                const type = line.slice(6).trim();
                currentEvent.type = type === 'done' ? 'done' : 'message';
                continue;
            }
            if (line.startsWith('data:')) {
                currentEvent.data.push(line.slice(5).trim());
            }
        }

        // 处理最后一个事件（如果没有以空行结尾）
        if (currentEvent.data.length) {
            const dataStr = currentEvent.data.join('\n');
            if (currentEvent.type === 'done') {
                try {
                    events.push({ done: true, payload: JSON.parse(dataStr) });
                } catch {
                    events.push({ done: true, payload: null });
                }
            } else {
                try {
                    const obj = JSON.parse(dataStr);
                    if (obj && typeof obj.delta === 'string') {
                        events.push({ delta: obj.delta });
                    }
                } catch (_) {
                    events.push({ delta: dataStr });
                }
            }
        }

        return events;
    }

    async function generatePromptStream(payload) {
        // 发起流式请求（默认）
        console.log('发起流式请求，payload:', payload);
        const resp = await fetch(`${baseUrl}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
            credentials: 'include',
            body: JSON.stringify(payload)
        });
        if (!resp.ok || !resp.body) {
            const txt = await resp.text();
            console.error('流式接口错误:', resp.status, txt);
            throw new Error(`流式接口错误: ${resp.status} ${txt}`);
        }
        console.log('响应头:', Object.fromEntries(resp.headers.entries()));
        const contentType = (resp.headers.get('content-type') || '').toLowerCase();
        // 非SSE回退：直接按JSON或纯文本处理，保证云端（如Vercel）兼容
        if (!contentType.includes('text/event-stream')) {
            try {
                const fallbackText = await resp.text();
                let parsed;
                try { parsed = JSON.parse(fallbackText); } catch (_) { parsed = null; }
                let promptText;
                if (parsed && typeof parsed === 'object' && parsed.prompt) {
                    promptText = parsed.prompt;
                } else {
                    // 客户端简易提取 <Instructions> 内容
                    const m = fallbackText.match(/<Instructions>([\s\S]*?)<\/Instructions>/i);
                    promptText = m ? m[1] : fallbackText;
                }
                promptDisplay.innerHTML = `<pre>${escapeHtml(promptText)}</pre>`;
                return { final: { prompt: promptText, variables: extractVariablesFromContent(promptText), version: 0, id: '' }, raw: promptText };
            } catch (e) {
                throw new Error('非SSE回退解析失败');
            }
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        let accumulated = '';
        // 重置完成事件标记，避免受上一次请求影响
        window._waitingForDoneData = false;
        console.log('开始读取流式响应...');
        // 仅渲染 <Instructions> 内文本的前端门控过滤器
        const START_TAG = '<Instructions>';
        const END_TAG = '</Instructions>';
        let scanBuffer = '';
        let visibleLen = 0;
        let started = false;
        let ended = false;
        function filterByInstructionsDelta(deltaStr) {
            // 追加到扫描缓冲
            scanBuffer += deltaStr;

            // 若尚未找到起始标签，继续等待
            if (!started) {
                // 使用不区分大小写的查找，避免大小写差异
                const lower = scanBuffer.toLowerCase();
                const sIdx = lower.indexOf(START_TAG.toLowerCase());
                if (sIdx === -1) {
                    // 仅保留起始哨兵所需的尾部，避免内存增长
                    if (scanBuffer.length > START_TAG.length - 1) {
                        scanBuffer = scanBuffer.slice(-(START_TAG.length - 1));
                    }
                    return '';
                }
                started = true;
                // 丢弃起始标签及其之前的内容
                scanBuffer = scanBuffer.slice(sIdx + START_TAG.length);
                visibleLen = 0; // 从空可见内容开始
            }

            // 计算当前可见区（起始到结束或缓冲末）
            const lowerBuf = scanBuffer.toLowerCase();
            const endLower = END_TAG.toLowerCase();
            const eIdx = lowerBuf.indexOf(endLower);
            let visible;
            if (eIdx === -1) {
                // 未检测到完整结束标签：
                // 防止把" </Instructions"未完整的前缀渲染出来。
                // 计算缓冲末尾与结束标签前缀的最长匹配长度，将该部分从可见文本中暂时剔除。
                const maxCheck = Math.min(lowerBuf.length, endLower.length - 1);
                let pending = 0;
                for (let k = maxCheck; k >= 1; k--) {
                    if (lowerBuf.slice(-k) === endLower.slice(0, k)) {
                        pending = k;
                        break;
                    }
                }
                visible = pending > 0 ? scanBuffer.slice(0, scanBuffer.length - pending) : scanBuffer;
            } else {
                visible = scanBuffer.slice(0, eIdx);
                ended = true;
            }

            // 输出相对于已发布长度的增量，避免重复
            const increment = visible.slice(visibleLen);
            visibleLen = visible.length;

            // 可选：限制缓冲增长（未结束时保留最近窗口）
            if (!ended && scanBuffer.length > 8192) {
                // 对齐 visibleLen 的裁剪
                const cut = scanBuffer.length - 4096; // 保留最近4K
                scanBuffer = scanBuffer.slice(cut);
                visibleLen = Math.max(0, visibleLen - cut);
            }
            return increment;
        }
        while (true) {
            const { value, done } = await reader.read();
            if (done) {
                console.log('流式响应读取完成');
                break;
            }
            const chunk = decoder.decode(value, { stream: true });
            console.log('收到数据块:', chunk);
            buffer += chunk;

            // 按行处理，每行可能是一个完整的SSE事件
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // 保留最后一个可能不完整的行

            for (const line of lines) {
                const trimmedLine = line.trim();
                if (!trimmedLine) continue;
                console.log('处理SSE行:', trimmedLine);

                // 1) 优先处理事件类型
                if (trimmedLine.startsWith('event:')) {
                    const eventType = trimmedLine.slice(6).trim();
                    if (eventType === 'done') {
                        console.log('收到完成事件标记');
                        window._waitingForDoneData = true;
                    }
                    continue;
                }

                // 2) 处理完成事件的数据帧
                if (window._waitingForDoneData && trimmedLine.startsWith('data:')) {
                    window._waitingForDoneData = false;
                    const dataStr = trimmedLine.slice(5).trim();
                    try {
                        const payload = JSON.parse(dataStr);
                        console.log('收到完成事件数据:', payload);
                        const resolved = resolveStreamedPrompt(payload, accumulated);
                        if (resolved.prompt) {
                            console.log('更新显示为提取后的内容，长度:', resolved.prompt.length);
                            promptDisplay.innerHTML = `<pre>${escapeHtml(resolved.prompt)}</pre>`;
                        }
                        return { final: resolved, raw: accumulated };
                    } catch (e) {
                        console.log('完成事件JSON解析失败:', e);
                        return { final: resolveStreamedPrompt(null, accumulated), raw: accumulated };
                    }
                }

                // 3) 普通增量数据
                if (trimmedLine.startsWith('data:')) {
                    const dataStr = trimmedLine.slice(5).trim();
                    try {
                        const obj = JSON.parse(dataStr);
                        if (obj && typeof obj.delta === 'string') {
                            // 只渲染 <Instructions> 内；未到达标签前不显示；大小写不敏感
                            const fragment = filterByInstructionsDelta(obj.delta);
                            if (fragment) {
                                accumulated += fragment;
                                console.log('更新显示(仅Instructions内)，当前累积长度:', accumulated.length, '增量片段长度:', fragment.length);
                                promptDisplay.innerHTML = `<pre>${escapeHtml(accumulated)}</pre>`;
                            }
                        }
                    } catch (e) {
                        console.log('JSON解析失败:', e, 'data:', dataStr);
                    }
                }
            }
        }
        // 处理可能残留的未分隔帧
        if (buffer) {
            const events = parseSSEChunk(buffer.replace(/\r\n/g, '\n'));
            for (const ev of events) {
                if (ev.delta) {
                    const fragment = typeof filterByInstructionsDelta === 'function' ? filterByInstructionsDelta(ev.delta) : ev.delta;
                    if (fragment) {
                        accumulated += fragment;
                    }
                }
                if (ev.done) {
                    const resolved = resolveStreamedPrompt(ev.payload, accumulated);
                    if (resolved.prompt) {
                        promptDisplay.innerHTML = `<pre>${escapeHtml(resolved.prompt)}</pre>`;
                    }
                    return { final: resolved, raw: accumulated };
                }
            }
        }
        return { final: null, raw: accumulated };
    }

    // 复制：流式生成到指定元素（不影响主显示区）
    async function generatePromptStreamToElement(payload, targetElement) {
        console.log('发起流式请求(对话框)，payload:', payload);
        const resp = await fetch(`${baseUrl}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
            credentials: 'include',
            body: JSON.stringify(payload)
        });
        if (!resp.ok || !resp.body) {
            const txt = await resp.text();
            throw new Error(`流式接口错误: ${resp.status} ${txt}`);
        }
        const contentType = (resp.headers.get('content-type') || '').toLowerCase();
        if (!contentType.includes('text/event-stream')) {
            const fallbackText = await resp.text();
            let parsed; try { parsed = JSON.parse(fallbackText); } catch (_) { parsed = null; }
            let promptText;
            if (parsed && typeof parsed === 'object' && parsed.prompt) promptText = parsed.prompt; else {
                const m = fallbackText.match(/<Instructions>[\s\S]*?<\/Instructions>/i);
                promptText = m ? m[0].replace(/<\/?Instructions>/gi, '') : fallbackText;
            }
            if (targetElement) targetElement.innerHTML = `<pre>${escapeHtml(promptText)}</pre>`;
            return { final: { prompt: promptText, variables: extractVariablesFromContent(promptText), version: 0, id: '' }, raw: promptText };
        }
        const reader = resp.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        let accumulated = '';
        window._waitingForDoneData = false;
        const START_TAG = '<Instructions>';
        const END_TAG = '</Instructions>';
        let scanBuffer = '';
        let visibleLen = 0;
        let started = false;
        let ended = false;
        function filterByInstructionsDelta(deltaStr) {
            scanBuffer += deltaStr;
            if (!started) {
                const lower = scanBuffer.toLowerCase();
                const sIdx = lower.indexOf(START_TAG.toLowerCase());
                if (sIdx === -1) {
                    if (scanBuffer.length > START_TAG.length - 1) scanBuffer = scanBuffer.slice(-(START_TAG.length - 1));
                    return '';
                }
                started = true;
                scanBuffer = scanBuffer.slice(sIdx + START_TAG.length);
                visibleLen = 0;
            }
            const lowerBuf = scanBuffer.toLowerCase();
            const endLower = END_TAG.toLowerCase();
            const eIdx = lowerBuf.indexOf(endLower);
            let visible;
            if (eIdx === -1) {
                const maxCheck = Math.min(lowerBuf.length, endLower.length - 1);
                let pending = 0;
                for (let k = maxCheck; k >= 1; k--) {
                    if (lowerBuf.slice(-k) === endLower.slice(0, k)) { pending = k; break; }
                }
                visible = pending > 0 ? scanBuffer.slice(0, scanBuffer.length - pending) : scanBuffer;
            } else {
                visible = scanBuffer.slice(0, eIdx);
                ended = true;
            }
            const increment = visible.slice(visibleLen);
            visibleLen = visible.length;
            return increment;
        }
        // 保持调用者设置的loading占位，直到首个片段到来
        let pre = targetElement ? targetElement.querySelector('pre') : null;
        let preInitialized = !!pre;
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            buffer += chunk;
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            for (const line of lines) {
                const t = line.trim();
                if (!t) continue;
                if (t.startsWith('event:')) { if (t.slice(6).trim() === 'done') window._waitingForDoneData = true; continue; }
                if (window._waitingForDoneData && t.startsWith('data:')) {
                    window._waitingForDoneData = false;
                    try {
                        const payload = JSON.parse(t.slice(5).trim());
                        const resolved = resolveStreamedPrompt(payload, accumulated);
                        if (resolved.prompt) {
                            if (!pre) {
                                targetElement.innerHTML = '';
                                pre = document.createElement('pre');
                                targetElement.appendChild(pre);
                            }
                            pre.textContent = resolved.prompt;
                        }
                        return { final: resolved, raw: accumulated };
                    } catch { return { final: resolveStreamedPrompt(null, accumulated), raw: accumulated }; }
                }
                if (t.startsWith('data:')) {
                    try {
                        const obj = JSON.parse(t.slice(5).trim());
                        if (obj && typeof obj.delta === 'string') {
                            const fragment = filterByInstructionsDelta(obj.delta);
                            if (fragment) {
                                accumulated += fragment;
                                if (!pre) {
                                    // 首次收到片段：替换loading为内容区域
                                    targetElement.innerHTML = '';
                                    pre = document.createElement('pre');
                                    targetElement.appendChild(pre);
                                }
                                pre.textContent = accumulated;
                            }
                        }
                    } catch (_) { }
                }
            }
        }
        return { final: null, raw: accumulated };
    }

    // 旧的 handleGeneratePrompt 函数已移除，现在使用弹窗生成功能

    // ========== 多条 User Message 处理 ==========
    
    // 文件转 base64
    function fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    // 从模板构建多模态 User Content
    // 模板示例: "这是参考答案：{$KNOWLEDGE}\n这是学生作答：{$ANSWER}"
    // 返回: [{type: "text", text: "..."}, {type: "image_url", ...}, ...]
    function buildUserContentFromTemplate(template, variablesData) {
        const content = [];
        
        // 使用正则表达式分割模板，保留变量占位符
        // 匹配 {$VAR_NAME} 格式
        const varPattern = /\{\$([A-Za-z_][A-Za-z0-9_]*)\}/g;
        
        let lastIndex = 0;
        let match;
        
        while ((match = varPattern.exec(template)) !== null) {
            // 添加变量前的文本
            if (match.index > lastIndex) {
                const textBefore = template.substring(lastIndex, match.index);
                if (textBefore.trim()) {
                    content.push({ type: "text", text: textBefore });
                }
            }
            
            // 获取变量名和对应的值
            const varName = match[1];
            const varData = variablesData[varName];
            
            if (varData) {
                // 添加变量的文本内容
                if (varData.text && varData.text.trim()) {
                    content.push({ type: "text", text: varData.text });
                }
                // 添加变量的图片
                if (varData.images && varData.images.length > 0) {
                    for (const imgBase64 of varData.images) {
                        content.push({ type: "image_url", image_url: { url: imgBase64 } });
                    }
                }
            } else {
                // 变量未定义，保留占位符
                content.push({ type: "text", text: `{$${varName}}` });
            }
            
            lastIndex = match.index + match[0].length;
        }
        
        // 添加最后一段文本
        if (lastIndex < template.length) {
            const textAfter = template.substring(lastIndex);
            if (textAfter.trim()) {
                content.push({ type: "text", text: textAfter });
            }
        }
        
        // 如果模板为空或没有解析出内容，返回空数组
        return content;
    }

    // 运行测试
    async function handleRunTest() {
        // 优先使用 System Prompt 文本框中的内容，其次使用已选提示词
        const systemText = systemPromptEl && systemPromptEl.value.trim() ? systemPromptEl.value : currentPrompt;
        if (!systemText) {
            showNotification("请先在 System Prompt 中填入内容，或生成/选择一个提示词", "warning");
            return;
        }

        // 替换 System Prompt 中的变量（仅文本替换）
        let testPrompt = systemText;
        for (const [variable, varData] of Object.entries(variableValuesWithMedia)) {
            const regex = new RegExp(`\\{\\$${variable}\\}`, "g");
            // System Prompt 只替换文本部分
            testPrompt = testPrompt.replace(regex, varData.text || `{$${variable}}`);
        }

        // 获取选中的模型
        const modelSelect = document.querySelector("#model-select");
        const model = modelSelect ? modelSelect.value : "deepseek-v3-huoshan";

        // 获取 User Prompt 模板
        const userPromptTemplate = userPromptEl ? userPromptEl.value.trim() : '';

        try {
            // 显示加载状态
            testResult.innerHTML = '<div class="loading-pulse">正在测试中...</div>';

            // 构建请求体
            const requestBody = {
                system_prompt: testPrompt,
                model: model,
                max_tokens: 4096,
                project_id: currentProjectId
            };
            
            // 构建 User 消息内容
            let userContent = [];
            
            // 如果有 User Prompt 模板，解析并构建多模态内容
            if (userPromptTemplate) {
                userContent = buildUserContentFromTemplate(userPromptTemplate, variableValuesWithMedia);
            } else {
                // 没有模板时，直接将所有变量值按顺序拼接
                for (const [varName, varData] of Object.entries(variableValuesWithMedia)) {
                    if (varData.text && varData.text.trim()) {
                        userContent.push({ type: "text", text: varData.text });
                    }
                    if (varData.images && varData.images.length > 0) {
                        for (const imgBase64 of varData.images) {
                            userContent.push({ type: "image_url", image_url: { url: imgBase64 } });
                        }
                    }
                }
            }
            
            console.log("[DEBUG] userPromptTemplate:", userPromptTemplate);
            console.log("[DEBUG] variableValuesWithMedia:", variableValuesWithMedia);
            console.log("[DEBUG] 构建的 userContent:", userContent);
            
            if (userContent.length > 0) {
                requestBody.user_messages = [{ content: userContent }];
            }
            
            // 调试日志：打印完整请求体
            console.log("[DEBUG] 发送请求体:", JSON.stringify(requestBody, (key, value) => {
                // 截断 base64 图片数据
                if (typeof value === 'string' && value.startsWith('data:image')) {
                    return value.substring(0, 50) + '...[base64 truncated]';
                }
                return value;
            }, 2));
            
            const resp = await fetch(`${baseUrl}/test/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
                credentials: 'include',
                body: JSON.stringify(requestBody)
            });

            // 如果后端不支持SSE，回退到原非流式
            const contentType = (resp.headers.get('content-type') || '').toLowerCase();
            if (!resp.ok) {
                const errText = await resp.text();
                throw new Error(errText || '测试失败');
            }
            if (!contentType.includes('text/event-stream') || !resp.body) {
                const fallback = await resp.json();
                testResult.innerHTML = `<pre>${escapeHtml(fallback.result || '')}</pre>`;
                showNotification("测试完成", "success");
                return;
            }

            const reader = resp.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';
            let acc = '';
            testResult.innerHTML = '<pre></pre>';
            const pre = testResult.querySelector('pre');

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                for (const line of lines) {
                    const t = line.trim();
                    if (!t) continue;
                    if (t.startsWith('event:')) continue;
                    if (t.startsWith('data:')) {
                        const dataStr = t.slice(5).trim();
                        try {
                            const obj = JSON.parse(dataStr);
                            if (obj.delta != null) {
                                acc += obj.delta;
                                pre.textContent = acc;
                            } else if (obj.result != null) {
                                pre.textContent = obj.result;
                            }
                        } catch (_) {
                            // 忽略无法解析的片段
                        }
                    }
                }
            }
            showNotification("测试完成", "success");
        } catch (error) {
            console.error("测试失败:", error);
            testResult.innerHTML = '<div class="prompt-placeholder">测试失败，请重试</div>';
            showNotification("测试失败: " + error.message, "error");
        }
    }

    // 开始优化提示词
    async function handleStartImprove() {
        if (!currentPrompt) {
            showNotification("请先生成或选择一个提示词", "warning");
            return;
        }

        const instructions = improveInstructions.value.trim();
        if (!instructions) {
            showNotification("请输入优化说明", "warning");
            return;
        }

        try {
            // 隐藏输入区域，显示全局loading状态
            improveInputSection.classList.add("hidden");
            improveLoadingSection.classList.remove("hidden");
            startImproveBtn.disabled = true;

            console.log("第一步：调用improve接口获取优化思路和初步优化结果");
            // 第一步：调用 improve 接口获取优化思路和初步优化结果
            const improveResponse = await fetch(`${baseUrl}/improve`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...getAuthHeaders()
                },
                credentials: 'include',
                body: JSON.stringify({
                    project_id: currentProjectId,
                    prompt_id: currentPromptId,
                    metaprompt: currentPrompt,
                    improve_instructions: instructions
                })
            });

            if (!improveResponse.ok) {
                const errorData = await improveResponse.json();
                throw new Error(errorData.detail || "优化第一步失败");
            }

            const improveResult = await improveResponse.json();
            console.log("improve接口返回结果:", improveResult);

            // 获取优化思路和初步提示词 - 注意这里使用正确的字段名writing_prompts
            const planning = improveResult.planning;
            const initialPrompt = improveResult.writing_prompts;  // 修正字段名

            // 在后台准备初步优化规划和初步提示词内容
            improvePlanning.innerHTML = `<pre>${escapeHtml(planning)}</pre>`;
            improvePromptContent.innerHTML = `<pre>${escapeHtml(initialPrompt)}</pre>`;

            console.log("第二步：调用revise接口获取最终优化结果");
            // 第二步：调用 revise 接口获取最终优化结果
            console.log("准备调用/revise接口，参数:", {
                project_id: currentProjectId,
                improve_instructions: instructions,
                planning: planning,
                prompt: initialPrompt
            });

            // 构建请求体，严格按照服务器期望的格式
            const reviseResponse = await fetch(`${baseUrl}/revise`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...getAuthHeaders()
                },
                credentials: 'include',
                body: JSON.stringify({
                    project_id: currentProjectId,
                    improve_instructions: instructions,
                    planning: planning,
                    prompt: initialPrompt
                })
            });

            if (!reviseResponse.ok) {
                const errorText = await reviseResponse.text();
                console.error("调用/revise接口失败:", reviseResponse.status, errorText);
                try {
                    const errorData = JSON.parse(errorText);
                    throw new Error(errorData.detail || `优化第二步失败 (${reviseResponse.status})`);
                } catch (e) {
                    if (e instanceof SyntaxError) {
                        throw new Error(`优化第二步失败 (${reviseResponse.status}): ${errorText}`);
                    } else {
                        throw e;
                    }
                }
            }

            const reviseResult = await reviseResponse.json();
            console.log("revise接口返回结果:", reviseResult);

            // 处理返回结果 - 根据服务器端代码，返回字段应该是 modification_plan 和 final_prompt
            const modificationPlan = reviseResult.modification_plan || "";
            const finalPrompt = reviseResult.final_prompt || "";

            // 更新优化结果
            improvementPlan.innerHTML = `<pre>${escapeHtml(modificationPlan)}</pre>`;
            improvedPrompt.innerHTML = `<pre>${escapeHtml(finalPrompt)}</pre>`;

            // 保存最终优化结果到临时变量
            improvedPromptContent = finalPrompt;

            // 提取变量
            improvedPromptVariables = extractVariables(improvedPromptContent);

            // 隐藏加载状态，显示优化结果
            improveLoadingSection.classList.add("hidden");
            improvementResultSection.classList.remove("hidden");

            // 切换到最终提示词标签
            switchImproveTab("revise-prompt");

            // 显示成功通知
            showNotification("提示词优化完成", "success");
        } catch (error) {
            console.error("优化失败:", error);
            // 显示错误通知
            showNotification("优化失败: " + error.message, "error");
            // 恢复输入区域显示
            improveInputSection.classList.remove("hidden");
            improveLoadingSection.classList.add("hidden");
        } finally {
            // 恢复按钮状态
            startImproveBtn.disabled = false;
        }
    }

    // 保存为新版本
    async function saveAsNewVersion() {
        if (!currentPrompt) {
            showNotification("请先生成或选择一个提示词", "warning");
            return;
        }

        const newVersion = promptDisplay.querySelector("#new-version").value.trim();
        if (!newVersion) {
            showNotification("请输入新版本号", "warning");
            return;
        }

        try {
            // 显示加载状态
            promptDisplay.innerHTML = '<div class="loading-pulse">正在保存新版本...</div>';

            const response = await fetch(`${baseUrl}/projects/${currentProjectId}/prompts/${currentPromptId}/versions`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    version: newVersion,
                    prompt: currentPrompt,
                    variables: currentVariables
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "保存新版本失败");
            }

            const result = await response.json();

            // 更新提示词和版本信息
            currentPrompt = result.prompt;
            currentPromptId = result.id;
            currentVariables = result.variables;

            // 更新版本显示
            currentVersion.textContent = `v${result.version}`;

            // 更新提示词显示
            promptDisplay.innerHTML = `<pre>${escapeHtml(result.prompt)}</pre>`;

            // 更新测试区域
            updateTestArea(result.variables);

            // 重新加载项目提示词列表
            await loadProjectPrompts(currentProjectId);

            // 显示成功通知
            showNotification("新版本保存成功", "success");
        } catch (error) {
            console.error("保存新版本失败:", error);
            promptDisplay.innerHTML = '<div class="prompt-placeholder">保存新版本失败，请重试</div>';
            showNotification("保存新版本失败: " + error.message, "error");
        }
    }

    // 获取用户信息
    async function getUserInfo() {
        try {
            console.log("尝试获取用户信息...");
            const response = await fetch(`${baseUrl}/auth/me`, {
                headers: getAuthHeaders(),
                credentials: 'include'  // 重要: 确保包含Cookie
            });

            if (response.status === 401) {
                console.log("用户未登录 (401), 重定向到登录页");

                // 通过检查当前URL确认是否已经在登录页面，防止循环重定向
                if (!window.location.pathname.includes('/auth/login-page')) {
                    window.location.href = '/auth/login-page';
                }
                return null;
            }

            if (!response.ok) {
                console.error("获取用户信息失败, HTTP状态码:", response.status);
                throw new Error("获取用户信息失败");
            }

            const user = await response.json();
            console.log("成功获取用户信息:", user.username);
            return user;
        } catch (error) {
            console.error("获取用户信息出错:", error);
            return null;
        }
    }

    // 添加授权头的函数
    function getAuthHeaders() {
        // 尝试从localStorage获取令牌
        const token = localStorage.getItem('access_token');
        if (token) {
            return { 'Authorization': `Bearer ${token}` };
        }

        // 使用Cookie认证时无需添加其他头
        // 浏览器会自动在请求中包含Cookie
        return {};
    }

    // 添加用户信息元素和登出按钮
    async function initUserInfo() {
        console.log("初始化用户信息...");

        // 获取用户信息
        const user = await getUserInfo();
        if (!user) {
            console.log("无法获取用户信息，不显示用户界面元素");
            return;
        }

        console.log("创建用户信息界面元素");
        // 创建用户信息元素
        const userInfoContainer = document.createElement('div');
        userInfoContainer.className = 'user-info-container';

        userInfoContainer.innerHTML = `
            <div class="user-info">
                <span class="username">${escapeHtml(user.username)}</span>
            </div>
            <a href="javascript:void(0)" class="logout-btn" id="logout-btn" title="退出登录">
                <i class="ri-logout-box-line"></i>
            </a>
        `;

        // 添加到侧边栏
        if (sidebar) {
            sidebar.insertBefore(userInfoContainer, sidebar.firstChild);
            console.log("用户信息元素已添加到侧边栏");

            // 添加登出事件监听
            setTimeout(() => {
                const logoutBtn = document.getElementById('logout-btn');
                if (logoutBtn) {
                    logoutBtn.addEventListener('click', async function (e) {
                        e.preventDefault();
                        console.log("处理退出登录...");
                        await handleLogout();
                    });
                    console.log("已添加登出按钮事件监听器");
                } else {
                    console.warn("无法找到登出按钮元素");
                }
            }, 100);
        } else {
            console.warn("找不到侧边栏元素，无法添加用户信息");
        }

        // 添加样式
        const style = document.createElement('style');
        style.textContent = `
            .user-info-container {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 15px;
                border-bottom: 1px solid var(--border-color);
                margin-bottom: 10px;
            }
            
            .user-info .username {
                font-weight: 500;
                color: var(--primary-color);
            }
            
            .logout-btn {
                display: none; /* 隐藏退出登录按钮 */
                color: var(--text-dim);
                text-decoration: none;
                transition: color 0.2s;
            }
            
            .logout-btn:hover {
                color: var(--danger-color);
            }
        `;

        document.head.appendChild(style);
    }

    // Global handler for logout (called from index.html)
    window.handleLogoutNav = async function () {
        if (confirm("确定要退出登录吗？")) {
            await handleLogout();
        }
    };

    async function handleLogout() {
        try {
            const response = await fetch(`${baseUrl}/auth/logout`, {
                method: "POST",
                headers: getAuthHeaders(),
                credentials: 'include'
            });

            // Set flag for auth check
            sessionStorage.setItem('just_logged_out', 'true');

            // Redirect to login page
            window.location.href = "/auth/login-page?logout=success";
        } catch (error) {
            console.error("退出登录过程中出错:", error);
            showNotification("退出登录过程中出错", "error");
        }
    }

    // 从提示词中提取变量
    function extractVariables(text) {
        if (!text) return [];

        const variables = [];
        // 匹配 {{variable_name}} 格式的变量
        const regex = /\{\{([^}]+)\}\}/g;
        let match;

        while ((match = regex.exec(text)) !== null) {
            const varName = match[1].trim();
            // 避免重复添加变量
            if (!variables.includes(varName)) {
                variables.push(varName);
            }
        }

        return variables;
    }

    // 保存优化后的提示词
    async function saveImprovedPrompt() {
        if (!improvedPromptContent) {
            showNotification("没有优化结果可保存", "warning");
            return;
        }

        try {
            // 显示保存中状态
            showNotification("正在保存优化结果...", "info");

            // 直接使用变量数组
            const saveResponse = await fetch(`${baseUrl}/api/prompts`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders()
                },
                body: JSON.stringify({
                    project_id: currentProjectId,
                    system_prompt: improvedPromptContent,
                    user_prompt: '',
                    name: `优化版 ${new Date().toLocaleString('zh-CN')}`,
                    variables: improvedPromptVariables  // 直接使用变量数组
                })
            });

            if (!saveResponse.ok) {
                throw new Error(`保存失败: ${saveResponse.status}`);
            }

            const saveData = await saveResponse.json();
            console.log("保存优化后的提示词成功:", saveData);

            // 更新提示词列表
            await loadProjectPrompts(currentProjectId);

            // 更新当前提示词显示
            currentPrompt = improvedPromptContent;
            currentPromptId = saveData.id;
            currentVariables = improvedPromptVariables.map(v => v.name);

            // 更新版本显示
            currentVersion.textContent = `v${saveData.version || 1}`;

            // 更新提示词显示
            promptDisplay.innerHTML = `<pre>${escapeHtml(improvedPromptContent)}</pre>`;

            // 更新测试区域
            updateTestArea(currentVariables);

            // 关闭优化对话框
            hideImproveDialog();

            showNotification("优化后的提示词已保存", "success");
        } catch (error) {
            console.error("保存优化后的提示词失败:", error);
            showNotification(`保存失败: ${error.message}`, "error");
        }
    }

    // 显示项目重命名对话框
    function showRenameDialog() {
        if (!currentProjectId) {
            showNotification("请先选择一个项目", "warning");
            return;
        }

        // 设置输入框默认值为当前项目名称
        newProjectNameInput.value = currentProjectName.textContent;

        // 显示对话框
        renameDialog.style.display = "flex";

        // 聚焦到输入框并全选文本
        setTimeout(() => {
            newProjectNameInput.focus();
            newProjectNameInput.select();
        }, 100);
    }

    // 隐藏项目重命名对话框
    function hideRenameDialog() {
        renameDialog.style.display = "none";
    }

    // 处理项目重命名
    async function handleRenameProject() {
        const newName = newProjectNameInput.value.trim();

        if (!newName) {
            showNotification("请输入项目名称", "warning");
            return;
        }

        if (!currentProjectId) {
            showNotification("未选择项目", "error");
            hideRenameDialog();
            return;
        }

        try {
            // 显示加载状态
            confirmRenameBtn.disabled = true;
            confirmRenameBtn.textContent = "处理中...";

            console.log(`尝试重命名项目: ID=${currentProjectId}, 新名称=${newName}`);

            const response = await fetch(`${baseUrl}/api/projects/${currentProjectId}/rename`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    ...getAuthHeaders()
                },
                credentials: 'include',
                body: JSON.stringify({
                    name: newName
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error("重命名项目HTTP错误:", response.status, errorData);
                throw new Error(errorData.detail || errorData.message || "重命名项目失败");
            }

            const result = await response.json();
            console.log("重命名项目响应:", result);

            // 检查响应格式
            if (!result.success) {
                throw new Error(result.message || "重命名项目失败");
            }

            // 更新项目名称
            currentProjectName.textContent = newName;

            // 更新项目列表中的项目名称
            const projectItem = projectList.querySelector(`.project-item[data-id="${currentProjectId}"]`);
            if (projectItem) {
                const projectNameElem = projectItem.querySelector(".project-name");
                if (projectNameElem) {
                    projectNameElem.textContent = newName;
                }
            }

            // 隐藏对话框
            hideRenameDialog();

            // 显示成功通知
            showNotification("项目重命名成功", "success");
        } catch (error) {
            console.error("重命名项目失败:", error);
            showNotification("重命名项目失败: " + error.message, "error");
        } finally {
            // 恢复按钮状态
            confirmRenameBtn.disabled = false;
            confirmRenameBtn.textContent = "确认";
        }
    }

    // 显示项目删除确认对话框
    function showDeleteDialog() {
        if (!currentProjectId) {
            showNotification("请先选择一个项目", "warning");
            return;
        }

        // 显示对话框
        deleteDialog.style.display = "flex";
    }

    // 隐藏项目删除确认对话框
    function hideDeleteDialog() {
        deleteDialog.style.display = "none";
    }

    // A处理项目删除
    async function handleDeleteProject() {
        if (!currentProjectId) {
            showNotification("未选择项目", "error");
            hideDeleteDialog();
            return;
        }

        try {
            // 显示加载状态
            confirmDeleteBtn.disabled = true;
            confirmDeleteBtn.textContent = "删除中...";

            console.log(`尝试删除项目: ID=${currentProjectId}`);

            const response = await fetch(`${baseUrl}/api/projects/${currentProjectId}`, {
                method: "DELETE",
                headers: getAuthHeaders(),
                credentials: 'include'
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error("删除项目HTTP错误:", response.status, errorData);
                throw new Error(errorData.detail || errorData.message || "删除项目失败");
            }

            const result = await response.json();
            console.log("删除项目响应:", result);

            // 检查响应格式
            if (!result.success) {
                throw new Error(result.message || "删除项目失败");
            }

            // 从项目列表中移除该项目
            const projectItem = projectList.querySelector(`.project-item[data-id="${currentProjectId}"]`);
            if (projectItem) {
                projectItem.remove();
            }

            // 隐藏对话框
            hideDeleteDialog();

            // 重置当前项目
            currentProjectId = null;
            currentProjectName.textContent = "未选择项目";

            // 隐藏项目操作按钮
            toggleProjectActions(false);

            // 清空提示词显示区
            resetPromptDisplay();

            // 显示空项目视图
            if (projectList.children.length === 0) {
                document.querySelector('.empty-project-view').style.display = 'flex';
                document.querySelector('.workspace-container').style.display = 'none';
            }

            // 显示成功通知
            showNotification("项目删除成功", "success");
        } catch (error) {
            console.error("删除项目失败:", error);
            showNotification("删除项目失败: " + error.message, "error");
        } finally {
            // 恢复按钮状态
            confirmDeleteBtn.disabled = false;
            confirmDeleteBtn.textContent = "删除项目";
        }
    }

    // 切换编辑/查看模式
    function toggleEditMode() {
        if (!currentPrompt || !currentPromptId) {
            showNotification("请先生成或选择一个提示词", "warning");
            return;
        }

        // 检查是否已处于编辑模式
        const icon = editPromptBtn.querySelector("i");
        const isEditing = icon && icon.classList.contains("ri-save-line");

        if (isEditing) {
            // 如果当前是编辑模式，执行保存操作
            saveEditedPrompt();
        } else {
            // 如果当前是查看模式，切换到编辑模式

            // 保存原始内容以便取消时恢复
            const originalContent = currentPrompt;

            // 创建文本框 - 使用 Tailwind 类
            const textarea = document.createElement("textarea");
            textarea.className = "w-full h-full bg-white border border-[var(--border-subtle)] rounded-xl p-4 text-sm text-[var(--text-secondary)] focus:border-[var(--accent-primary)] focus:ring-2 focus:ring-[var(--accent-primary)]/5 outline-none transition-all resize-none font-mono leading-relaxed shadow-inner";
            textarea.value = currentPrompt;

            // 替换显示区域
            promptDisplay.innerHTML = '';
            promptDisplay.appendChild(textarea);
            promptDisplay.classList.remove('p-4'); // Remove padding from container to let textarea fill

            // 聚焦文本框并将光标放在末尾
            textarea.focus();
            textarea.setSelectionRange(textarea.value.length, textarea.value.length);

            // 更改编辑按钮为保存按钮
            editPromptBtn.innerHTML = '<i class="ri-save-line"></i> 保存';
            editPromptBtn.classList.remove('text-[var(--text-dim)]');
            editPromptBtn.classList.add('text-[var(--accent-primary)]');

            // 添加取消按钮
            const cancelButton = document.createElement("button");
            cancelButton.className = "text-[11px] font-bold text-[var(--text-dim)] hover:text-[var(--text-primary)] transition-colors ml-4";
            cancelButton.innerHTML = '<i class="ri-close-line"></i> 取消';
            cancelButton.id = "cancel-edit-btn";

            // 将取消按钮添加到工具栏
            const actionButtonGroup = editPromptBtn.parentElement;
            actionButtonGroup.appendChild(cancelButton);

            // 绑定取消按钮事件
            cancelButton.addEventListener("click", () => {
                // 恢复原始内容
                promptDisplay.innerHTML = `<pre>${escapeHtml(originalContent)}</pre>`;
                promptDisplay.classList.add('p-4');

                // 恢复编辑按钮
                editPromptBtn.innerHTML = '直接编辑';
                editPromptBtn.classList.add('text-[var(--text-dim)]');
                editPromptBtn.classList.remove('text-[var(--accent-primary)]');

                // 移除取消按钮
                cancelButton.remove();
            });
        }
    }

    // 保存编辑后的提示词
    async function saveEditedPrompt() {
        if (!currentPromptId) {
            showNotification("无法保存：未找到当前提示词ID", "error");
            return;
        }

        try {
            // 获取文本框内容
            const textarea = promptDisplay.querySelector("textarea");
            if (!textarea) {
                showNotification("无法获取编辑内容", "error");
                return;
            }

            const newContent = textarea.value.trim();
            if (!newContent) {
                showNotification("提示词内容不能为空", "warning");
                return;
            }

            // 获取 User Prompt 内容
            const userPromptContent = userPromptEl ? userPromptEl.value.trim() : '';

            // 显示加载状态
            promptDisplay.innerHTML = '<div class="loading">正在保存提示词...</div>';

            // 从提示词中提取变量
            const extractedVariables = extractVariablesFromContent(newContent);
            // 也从 User Prompt 中提取变量
            if (userPromptContent) {
                const userVars = extractVariablesFromContent(userPromptContent);
                userVars.forEach(v => {
                    if (!extractedVariables.includes(v)) {
                        extractedVariables.push(v);
                    }
                });
            }

            // 调用API更新提示词（PUT 更新当前版本，而非创建新版本）
            const response = await fetch(`${baseUrl}/api/prompts/${currentPromptId}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    ...getAuthHeaders()
                },
                credentials: 'include',
                body: JSON.stringify({
                    system_prompt: newContent,
                    user_prompt: userPromptContent,
                    variables: extractedVariables
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || errorData.message || "保存提示词失败");
            }

            const result = await response.json();

            // 更新提示词内容
            currentPrompt = newContent;

            // 更新变量
            currentVariables = extractedVariables;

            // 重新加载项目提示词列表以更新版本
            await loadProjectPrompts(currentProjectId);

            // 恢复显示模式
            promptDisplay.innerHTML = `<pre>${escapeHtml(currentPrompt)}</pre>`;
            promptDisplay.classList.add('p-4');

            // 恢复编辑按钮
            editPromptBtn.innerHTML = '直接编辑';
            editPromptBtn.classList.add('text-[var(--text-dim)]');
            editPromptBtn.classList.remove('text-[var(--accent-primary)]');

            // 移除取消按钮
            const cancelButton = document.getElementById("cancel-edit-btn");
            if (cancelButton) {
                cancelButton.remove();
            }

            // 更新测试区域变量
            updateTestArea(currentVariables);

            // 显示成功通知
            showNotification("提示词已保存", "success");

        } catch (error) {
            console.error("保存提示词失败:", error);
            // 恢复显示模式
            promptDisplay.innerHTML = `<pre>${escapeHtml(currentPrompt)}</pre>`;
            promptDisplay.classList.add('p-4');

            // 恢复编辑按钮
            editPromptBtn.innerHTML = '直接编辑';
            editPromptBtn.classList.add('text-[var(--text-dim)]');
            editPromptBtn.classList.remove('text-[var(--accent-primary)]');

            // 移除取消按钮
            const cancelButton = document.getElementById("cancel-edit-btn");
            if (cancelButton) {
                cancelButton.remove();
            }

            showNotification("保存提示词失败: " + error.message, "error");
        }
    }
});
