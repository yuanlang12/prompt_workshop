/** 提示词工坊 Tailwind 构建配置。
 *  维护者说明：修改模板/JS 中的样式类后，运行 scripts/build_css.sh 重新生成
 *  static/css/tailwind.css（产物已提交，部署无需 Node 环境）。
 */
module.exports = {
  content: ["templates/**/*.html", "static/js/*.js", "static/*.html"],
  theme: {
    extend: {},
  },
  plugins: [],
};
