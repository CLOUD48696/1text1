import { expect, test } from "@playwright/test";

test("create, confirm, stream, reconnect, finish and inspect evidence", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "开启一场新讨论" }),
  ).toBeVisible();
  await expect(page.locator(".discussion-card").first()).toBeVisible();
  expect(await page.locator(".discussion-card").count()).toBeGreaterThanOrEqual(
    5,
  );
  await page
    .getByLabel("讨论话题", { exact: true })
    .fill("小团队应该优先使用 AI 编程工具还是增加招聘？");
  await page.getByRole("button", { name: "生成嘉宾阵容" }).click();
  await expect(
    page.getByRole("heading", { name: "嘉宾已就位，讨论由你开启。" }),
  ).toBeVisible();
  await expect(page.locator(".roster-card")).toHaveCount(5);
  const id = page.url().split("#")[1];
  let state = await (await page.request.get(`/api/discussions/${id}`)).json();
  expect(state.messages).toHaveLength(0);
  await page.getByRole("button", { name: "确认阵容，开始讨论" }).click();
  await expect(page.locator(".message").first()).toBeVisible();
  await page.reload();
  await expect(page.getByText("本场讨论已结束", { exact: true })).toBeVisible();
  await expect(page.locator(".message")).toHaveCount(7);
  state = await (await page.request.get(`/api/discussions/${id}`)).json();
  expect(state.discussion.status).toBe("completed");
  expect(state.insights.length).toBeGreaterThan(0);
  expect(
    state.messages.filter((m: { content: string }) =>
      m.content.includes("欢迎来到本场圆桌"),
    ),
  ).toHaveLength(1);
  if (info.project.name === "mobile")
    await page.getByRole("button", { name: "观点", exact: true }).click();
  await expect(page.locator(".insight-card").first()).toBeVisible();
  await page.locator(".evidence button").first().click();
  await expect(page.locator(".message.referenced")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
  await page.screenshot({
    path: `test-results/studio-${info.project.name}.png`,
  });
});

test("two rooms stay separate and joining a room does not restart it", async ({
  page,
  context,
}) => {
  const create = async (topic: string) => {
    const response = await page.request.post("/api/discussions", {
      data: { topic, expert_count: 2 },
    });
    return (await response.json()).discussion_id as string;
  };
  const a = await create("企业是否应该实行每周四天工作制？");
  const b = await create("高校课程如何允许学生使用生成式 AI？");
  for (const id of [a, b])
    await expect
      .poll(
        async () =>
          (await (await page.request.get(`/api/discussions/${id}`)).json())
            .discussion.status,
      )
      .toBe("ready");
  await Promise.all(
    [a, b].map((id) => page.request.post(`/api/discussions/${id}/start`)),
  );
  await page.goto(`/#${a}`);
  const other = await context.newPage();
  await other.goto(`/#${b}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "企业是否应该实行每周四天工作制？",
  );
  await expect(other.getByRole("heading", { level: 1 })).toHaveText(
    "高校课程如何允许学生使用生成式 AI？",
  );
  await expect(page.getByText("本场讨论已结束", { exact: true })).toBeVisible();
  await expect(
    other.getByText("本场讨论已结束", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(page.locator(".message")).toHaveCount(7);
  await expect(page.locator(".transcript-scroll")).not.toContainText(
    "高校课程",
  );
  await expect(other.locator(".transcript-scroll")).not.toContainText(
    "四天工作制",
  );
  await other.close();
});

test("invalid topic is blocked and existing seed transcript is readable", async ({
  page,
}, info) => {
  await page.goto("/");
  await page.getByLabel("讨论话题", { exact: true }).fill("   ");
  await expect(
    page.getByRole("button", { name: "生成嘉宾阵容" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "已结束", exact: true }).click();
  await page
    .locator(".discussion-card")
    .filter({ hasText: "小型软件团队" })
    .click();
  await expect(page.getByText("本场讨论已结束", { exact: true })).toBeVisible();
  if (info.project.name === "mobile") {
    await page.getByRole("button", { name: "嘉宾", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "圆桌嘉宾", exact: true }),
    ).toBeVisible();
  }
  expect(
    await page.evaluate(
      () => document.documentElement.scrollHeight <= innerHeight,
    ),
  ).toBe(true);
});
