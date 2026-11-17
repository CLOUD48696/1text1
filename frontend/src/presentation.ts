export const labels: Record<string, string> = {
  generating: "邀请嘉宾中",
  ready: "待开场",
  running: "讨论进行中",
  completed: "已结束",
  failed: "发生错误",
  interrupted: "已中断",
};
export const phases: Record<string, string> = {
  opening: "主持人开场",
  discussion: "观点交锋",
  synthesis: "梳理观点",
  closing: "主持人总结",
  roster: "准备阵容",
};
export const prompts = [
  "小型软件团队应该优先使用 AI 编程工具还是增加招聘？",
  "企业是否应实行每周四天工作制？",
  "高校课程应如何允许学生使用生成式 AI？",
];
export const terminal = (status: string) =>
  ["completed", "failed", "interrupted"].includes(status);
