# Simple React Rules for Frontend Development

## Clear Rules (No Thinking Required)

### Rule 1: State Management
```
✅ Use useState for:
- Form inputs
- Local UI state (open/close, active tab)
- Temporary data

✅ Use Zustand for:
- User authentication
- Global settings
- Data shared across many pages

✅ Use API data directly:
- Don't copy API data to Zustand unless needed
- Use the data from your API calls
```

### Rule 2: useEffect Dependencies
```
✅ Do this:
useEffect(() => {
  fetchData(userId);
}, [userId]); // Only primitives

❌ Never this:
useEffect(() => {
  fetchData(user.id);
}, [user]); // Object causes infinite loop
```

### Rule 3: Syncing Store State
```
✅ If you MUST sync with local state:
useEffect(() => {
  if (editedText !== task.description) {
    setEditedText(task.description);
  }
}, [task.description, editedText]);

❌ Never this:
useEffect(() => {
  setEditedText(task.description);
}, [task.description]); // Infinite loop
```

### Rule 4: Event Handlers
```
✅ Do this:
const handleSubmit = useCallback(() => {
  submitForm(data);
}, [data]);

<button onClick={handleSubmit}>Submit</button>

❌ Never this:
<button onClick={() => submitForm(data)}>Submit</button>
```

## Complete Examples

### Example 1: Form Component
```tsx
function TaskForm() {
  // ✅ useState for form inputs
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  
  // ✅ Zustand for global state if needed
  const { user } = useAuthStore();
  
  // ✅ Safe event handler
  const handleSubmit = useCallback(() => {
    createTask({ title, description, userId: user.id });
  }, [title, description, user.id]);
  
  return (
    <form onSubmit={handleSubmit}>
      <input 
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Task title"
      />
      <textarea 
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Description"
      />
      <button type="submit">Create Task</button>
    </form>
  );
}
```

### Example 2: Task Detail Page
```tsx
function TaskDetailPage({ taskId }) {
  // ✅ API data - use directly or with React Query
  const { data: task, isLoading } = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => getTask(taskId)
  });
  
  // ✅ Local state for editing
  const [isEditing, setIsEditing] = useState(false);
  const [editedTitle, setEditedTitle] = useState('');
  
  // ✅ Safe sync - only when needed
  useEffect(() => {
    if (task && editedTitle !== task.title) {
      setEditedTitle(task.title);
    }
  }, [task?.title, editedTitle]);
  
  // ✅ Safe event handler
  const handleSave = useCallback(() => {
    updateTask(taskId, { title: editedTitle });
    setIsEditing(false);
  }, [taskId, editedTitle]);
  
  if (isLoading) return <div>Loading...</div>;
  
  return (
    <div>
      {isEditing ? (
        <input
          value={editedTitle}
          onChange={(e) => setEditedTitle(e.target.value)}
        />
      ) : (
        <h1>{task?.title}</h1>
      )}
      <button onClick={() => setIsEditing(!isEditing)}>
        {isEditing ? 'Cancel' : 'Edit'}
      </button>
      {isEditing && (
        <button onClick={handleSave}>Save</button>
      )}
    </div>
  );
}
```

### Example 3: List with Items
```tsx
function TaskList() {
  // ✅ API data
  const { data: tasks } = useQuery({
    queryKey: ['tasks'],
    queryFn: getTasks
  });
  
  // ✅ Local UI state
  const [selectedTaskId, setSelectedTaskId] = useState(null);
  
  // ✅ Derived state - no extra useState
  const selectedTask = tasks?.find(t => t.id === selectedTaskId);
  
  return (
    <div>
      {tasks?.map(task => (
        <div 
          key={task.id}
          onClick={() => setSelectedTaskId(task.id)}
          className={selectedTaskId === task.id ? 'selected' : ''}
        >
          <h3>{task.title}</h3>
          <p>{task.description}</p>
        </div>
      ))}
      
      {selectedTask && (
        <TaskDetail task={selectedTask} />
      )}
    </div>
  );
}
```

## Quick Reference

| Need | Solution | Example |
|------|----------|---------|
| Form input | useState | `const [value, setValue] = useState('')` |
| Global auth | Zustand | `const { user } = useAuthStore()` |
| API data | Use directly | `const { data } = useQuery(...)` |
| Effect trigger | Primitive only | `}, [id])` not `}, [user])` |
| Sync state | Check first | `if (a !== b) setA(b)` |
| Event handler | useCallback | `const fn = useCallback(() => {}, [dep])` |
| Derived value | useMemo | `const value = useMemo(() => calc(a,b), [a,b])` |

## What to Avoid

1. **Don't** put objects in useEffect dependencies
2. **Don't** sync Zustand to local state without checking if different
3. **Don't** create inline functions in JSX
4. **Don't** use useState for API data (use the response directly)
5. **Don't** create multiple states for related data

## When to Use What

- **Component's own state** → useState
- **Form fields** → useState  
- **Open/closed modals** → useState
- **User login status** → Zustand
- **Theme preferences** → Zustand
- **API responses** → Use directly, no extra state
- **Calculated values** → useMemo or calculate in render

That's it. Follow these patterns and you won't get infinite loops.