-- Merge tool_comments into forum system
-- tool_comments becomes forum_replies on tool-linked threads

-- 1. Add tool_id FK to forum_threads
ALTER TABLE forum_threads ADD COLUMN tool_id UUID REFERENCES tools(id) ON DELETE SET NULL;
CREATE INDEX idx_threads_tool ON forum_threads(tool_id);

-- 2. Link existing auto-created threads to their tools
UPDATE forum_threads ft
SET tool_id = t.id
FROM tools t
WHERE ft.author_id = t.author_id
  AND ft.title LIKE t.name || ' —%'
  AND ft.tool_id IS NULL;

-- 3. Migrate tool_comments to forum_replies
INSERT INTO forum_replies (id, thread_id, author_id, body, created_at, updated_at)
SELECT tc.id, ft.id, tc.author_id, tc.body, tc.created_at, tc.updated_at
FROM tool_comments tc
JOIN tools t ON tc.tool_id = t.id
JOIN forum_threads ft ON ft.tool_id = t.id
WHERE NOT EXISTS (SELECT 1 FROM forum_replies fr WHERE fr.id = tc.id);

-- 4. Update reply counts
UPDATE forum_threads ft
SET reply_count = (SELECT COUNT(*) FROM forum_replies fr WHERE fr.thread_id = ft.id)
WHERE ft.tool_id IS NOT NULL;

-- 5. Drop tool_comments
DROP TABLE tool_comments;
