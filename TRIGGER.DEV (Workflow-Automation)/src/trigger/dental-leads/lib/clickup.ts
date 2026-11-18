import { fingerprintFromTask, LeadIndex } from "./dedupe.js";
import { requireEnv, sleep } from "./env.js";

const CLICKUP_BASE = "https://api.clickup.com/api/v2";

async function clickup<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const token = requireEnv("CLICKUP_API_KEY");

  for (let attempt = 1; attempt <= 4; attempt++) {
    const res = await fetch(`${CLICKUP_BASE}${path}`, {
      method: init.method ?? "GET",
      headers: { Authorization: token, "Content-Type": "application/json" },
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
    });
    if (res.status === 429 && attempt < 4) {
      await sleep(5000 * attempt);
      continue;
    }
    if (!res.ok) {
      const body = (await res.text()).slice(0, 300);
      throw new Error(`ClickUp ${init.method ?? "GET"} ${path} failed with HTTP ${res.status}: ${body}`);
    }
    return (await res.json()) as T;
  }
  throw new Error(`ClickUp ${path} failed after retries`);
}

export interface ClickUpSpace {
  id: string;
  name: string;
}
export interface ClickUpList {
  id: string;
  name: string;
}

export async function getWorkspaceId(): Promise<string> {
  const data = await clickup<{ teams: { id: string; name: string }[] }>("/team");
  const team = data.teams[0];
  if (!team) throw new Error("No ClickUp workspace found for this API token");
  return team.id;
}

export async function listSpaces(workspaceId: string): Promise<ClickUpSpace[]> {
  const data = await clickup<{ spaces: ClickUpSpace[] }>(`/team/${workspaceId}/space?archived=false`);
  return data.spaces;
}

export async function createSpace(workspaceId: string, name: string): Promise<ClickUpSpace> {
  return clickup<ClickUpSpace>(`/team/${workspaceId}/space`, {
    method: "POST",
    body: {
      name,
      multiple_assignees: false,
      features: {
        due_dates: { enabled: true, start_date: false, remap_due_dates: false, remap_closed_due_date: false },
        priorities: { enabled: true, priorities: [] },
        tags: { enabled: true },
      },
    },
  });
}

export async function listFolderlessLists(spaceId: string): Promise<ClickUpList[]> {
  const data = await clickup<{ lists: ClickUpList[] }>(`/space/${spaceId}/list?archived=false`);
  return data.lists;
}

export async function createFolderlessList(spaceId: string, name: string): Promise<ClickUpList> {
  return clickup<ClickUpList>(`/space/${spaceId}/list`, { method: "POST", body: { name } });
}

export async function createSpaceTag(spaceId: string, name: string, bg: string): Promise<void> {
  await clickup(`/space/${spaceId}/tag`, {
    method: "POST",
    body: { tag: { name, tag_fg: "#FFFFFF", tag_bg: bg } },
  });
}

export interface NewTask {
  name: string;
  markdownDescription: string;
  /** 1 urgent, 2 high, 3 normal, 4 low */
  priority: 1 | 2 | 3 | 4;
  tags: string[];
}

export async function createTask(listId: string, task: NewTask): Promise<{ id: string; url?: string }> {
  return clickup<{ id: string; url?: string }>(`/list/${listId}/task`, {
    method: "POST",
    body: {
      name: task.name,
      markdown_description: task.markdownDescription,
      priority: task.priority,
      tags: task.tags,
    },
  });
}

/** Add every task of one kind (normal or archived) in the list to the duplicate index. */
async function indexListTasks(listId: string, index: LeadIndex, archived: boolean): Promise<void> {
  for (let page = 0; page < 200; page++) {
    const data = await clickup<{ tasks: { name?: string; description?: string }[]; last_page?: boolean }>(
      `/list/${listId}/task?page=${page}&include_closed=true&subtasks=false${archived ? "&archived=true" : ""}`
    );
    for (const task of data.tasks) {
      const fingerprint = fingerprintFromTask(task);
      if (fingerprint) index.add(fingerprint);
    }
    if (data.tasks.length === 0 || data.last_page === true) break;
    await sleep(300);
  }
}

/**
 * Index of every practice already in the list: open, closed and archived tasks.
 * Tasks you deleted (in ClickUp's trash) are not included, so deleting a lead lets it come back.
 */
export async function getExistingLeadIndex(listId: string): Promise<LeadIndex> {
  const index = new LeadIndex();
  await indexListTasks(listId, index, false);
  try {
    await indexListTasks(listId, index, true);
  } catch (error) {
    // Archived tasks are a bonus check; do not stop the whole run if this call is refused.
    console.warn("Could not read archived tasks for duplicate check:", String(error).slice(0, 200));
  }
  return index;
}
