import { task } from "@trigger.dev/sdk";
import {
  createFolderlessList,
  createSpace,
  createSpaceTag,
  getWorkspaceId,
  listFolderlessLists,
  listSpaces,
} from "./lib/clickup.js";
import { requireEnv } from "./lib/env.js";

const SPACE_NAME = "Lead Generation";
const FALLBACK_SPACE_NAME = "Sales & CRM";
const LIST_NAME = "Dental Leads";

const TAGS: Record<string, string> = {
  "website-opportunity": "#D93025",
  "no-website": "#E8710A",
  "dead-site": "#B31412",
  "outdated-site": "#F9AB00",
  "has-email": "#188038",
  "website-unchecked": "#5F6368",
  "first-test-run": "#6B46C1",
};

/**
 * One-off setup. Run it once (manually), then copy the printed listId into CLICKUP_LIST_ID
 * in .env and in the Trigger.dev dashboard.
 */
export const setupClickup = task({
  id: "setup-clickup",
  run: async () => {
    requireEnv("CLICKUP_API_KEY");

    const workspaceId = await getWorkspaceId();
    const spaces = await listSpaces(workspaceId);

    let space = spaces.find((s) => s.name === SPACE_NAME);
    if (!space) {
      try {
        space = await createSpace(workspaceId, SPACE_NAME);
      } catch (error) {
        // Some free plans limit Spaces. Fall back to the Space ClickUp created at signup.
        console.warn(`Could not create "${SPACE_NAME}" Space, trying "${FALLBACK_SPACE_NAME}"`, String(error));
        space = spaces.find((s) => s.name === FALLBACK_SPACE_NAME);
        if (!space) throw error;
      }
    }

    const lists = await listFolderlessLists(space.id);
    const list = lists.find((l) => l.name === LIST_NAME) ?? (await createFolderlessList(space.id, LIST_NAME));

    const tagResults: Record<string, string> = {};
    for (const [name, color] of Object.entries(TAGS)) {
      try {
        await createSpaceTag(space.id, name, color);
        tagResults[name] = "created";
      } catch (error) {
        // Most likely the tag already exists.
        tagResults[name] = `skipped: ${String(error).slice(0, 120)}`;
      }
    }

    console.log(`Set CLICKUP_SPACE_ID=${space.id} and CLICKUP_LIST_ID=${list.id} in .env and the Trigger.dev dashboard`);
    return { workspaceId, spaceId: space.id, spaceName: space.name, listId: list.id, tags: tagResults };
  },
});
