"""
Ant Design Component Knowledge Base
Pre-cached component patterns to reduce token usage
"""

# Core component knowledge that model needs
ANTD_COMPONENTS = {
    "button": {
        "import": "import { Button } from 'antd';",
        "basic_usage": "<Button type='primary'>Click me</Button>",
        "types": ["primary", "default", "dashed", "text", "link"],
        "props": ["type", "size", "loading", "disabled", "danger", "onClick"],
        "example": """
<Button type="primary" size="large" loading={isLoading} onClick={handleClick}>
  Submit
</Button>"""
    },
    
    "form": {
        "import": "import { Form, Input, Button } from 'antd';",
        "basic_usage": """
const [form] = Form.useForm();

<Form form={form} layout="vertical" onFinish={onFinish}>
  <Form.Item name="username" label="Username" rules={[{ required: true }]}>
    <Input />
  </Form.Item>
  <Form.Item>
    <Button type="primary" htmlType="submit">Submit</Button>
  </Form.Item>
</Form>""",
        "props": ["form", "layout", "onFinish", "initialValues", "rules"]
    },
    
    "table": {
        "import": "import { Table } from 'antd';",
        "basic_usage": """
const columns = [
  { title: 'Name', dataIndex: 'name', key: 'name' },
  { title: 'Age', dataIndex: 'age', key: 'age', sorter: true },
];

const data = [
  { key: '1', name: 'John', age: 32 },
];

<Table columns={columns} dataSource={data} />""",
        "props": ["columns", "dataSource", "pagination", "loading", "rowSelection"]
    },
    
    "card": {
        "import": "import { Card } from 'antd';",
        "basic_usage": """
<Card title="Card Title" extra={<a href="#">More</a>}>
  <p>Card content</p>
</Card>""",
        "props": ["title", "extra", "loading", "bordered", "actions"]
    },
    
    "modal": {
        "import": "import { Modal } from 'antd';",
        "basic_usage": """
const [open, setOpen] = useState(false);

<Modal 
  title="Modal Title"
  open={open}
  onOk={() => setOpen(false)}
  onCancel={() => setOpen(false)}
>
  <p>Modal content</p>
</Modal>""",
        "props": ["open", "title", "onOk", "onCancel", "confirmLoading"]
    },
    
    "select": {
        "import": "import { Select } from 'antd';",
        "basic_usage": """
<Select
  defaultValue="option1"
  style={{ width: 200 }}
  onChange={handleChange}
  options={[
    { value: 'option1', label: 'Option 1' },
    { value: 'option2', label: 'Option 2' },
  ]}
/>""",
        "props": ["value", "onChange", "options", "placeholder", "mode"]
    },
    
    "datepicker": {
        "import": "import { DatePicker } from 'antd';",
        "basic_usage": "<DatePicker onChange={onChange} />",
        "props": ["value", "onChange", "format", "showTime", "disabledDate"]
    },
    
    "layout": {
        "import": "import { Layout, Menu } from 'antd';",
        "basic_usage": """
const { Header, Content, Footer, Sider } = Layout;

<Layout>
  <Sider>
    <Menu items={menuItems} />
  </Sider>
  <Layout>
    <Header>Header</Header>
    <Content>Content</Content>
    <Footer>Footer</Footer>
  </Layout>
</Layout>""",
        "props": ["style", "className"]
    }
}

# App type to component mapping
APP_TYPE_COMPONENTS = {
    "todo": ["form", "list", "checkbox", "button", "modal", "tag"],
    "crud": ["table", "form", "modal", "button", "message"],
    "dashboard": ["card", "statistic", "chart", "table", "layout"],
    "ecommerce": ["card", "carousel", "rate", "button", "drawer"],
    "social": ["card", "avatar", "comment", "list", "timeline"],
    "admin": ["layout", "menu", "table", "form", "tabs"],
    "blog": ["card", "typography", "tag", "pagination", "comment"],
    "movie": ["card", "rate", "carousel", "modal", "grid"]
}

def get_components_for_app_type(app_description: str) -> list:
    """
    Analyze app description and return relevant components
    """
    app_description_lower = app_description.lower()
    
    # Detect app type
    for app_type, components in APP_TYPE_COMPONENTS.items():
        if app_type in app_description_lower:
            return components
    
    # Default components for unknown app types
    return ["button", "form", "card", "table", "modal"]

def get_component_knowledge(component_names: list) -> str:
    """
    Get cached knowledge for specific components
    Returns formatted string with imports and usage
    """
    knowledge = []
    imports = set()
    
    for name in component_names:
        if name in ANTD_COMPONENTS:
            comp = ANTD_COMPONENTS[name]
            imports.add(comp["import"])
            knowledge.append(f"// {name.upper()} Component:")
            knowledge.append(comp["basic_usage"])
            knowledge.append("")
    
    # Combine imports
    import_section = "\n".join(sorted(imports))
    usage_section = "\n".join(knowledge)
    
    return f"""
// IMPORTS
{import_section}

// USAGE EXAMPLES
{usage_section}
"""

def get_minimal_component_context() -> str:
    """
    Return minimal context about available Ant Design components
    This goes into the system prompt to guide the model
    """
    return """
## ANT DESIGN COMPONENTS AVAILABLE

You have Ant Design (antd) 5.x available. Use these components directly without any Tailwind CSS:

**Core Components:**
- Button: type="primary|default|dashed|text|link"
- Form: With built-in validation using rules
- Input: Basic text input with placeholder
- Select: Dropdown with options array
- DatePicker: Date selection with format
- Table: Data grid with columns and dataSource
- Card: Container with title and content
- Modal: Dialog with open/onOk/onCancel
- Layout: Page structure with Header/Sider/Content/Footer
- Menu: Navigation with items array

**Key Points:**
- Import from 'antd': import { Button, Form, Input } from 'antd';
- No className with Tailwind classes needed
- Use style prop for custom styles: style={{ padding: 24 }}
- Forms use Form.Item for field wrapper
- Tables need columns array and dataSource array
- All components have built-in responsive behavior

**Example Pattern:**
```jsx
import { Button, Card, Form, Input } from 'antd';

function MyComponent() {
  const [form] = Form.useForm();
  
  return (
    <Card title="Title">
      <Form form={form} layout="vertical">
        <Form.Item name="field" rules={[{ required: true }]}>
          <Input placeholder="Enter value" />
        </Form.Item>
        <Button type="primary">Submit</Button>
      </Form>
    </Card>
  );
}
```

ALWAYS use Ant Design components instead of plain HTML elements or custom styling.
"""