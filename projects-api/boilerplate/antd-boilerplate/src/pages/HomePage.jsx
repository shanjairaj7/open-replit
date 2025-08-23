import React from 'react'
import { Button, Card, Space, Typography } from 'antd'

const { Title, Paragraph } = Typography

function HomePage() {
  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <Card>
        <Title level={2}>Welcome to Your Ant Design App</Title>
        <Paragraph>
          This boilerplate uses Ant Design components. No Tailwind CSS configuration needed!
        </Paragraph>
        <Paragraph>
          All components come with built-in styles and themes. Just import and use them.
        </Paragraph>
        <Space>
          <Button type="primary">Primary Button</Button>
          <Button>Default Button</Button>
          <Button type="dashed">Dashed Button</Button>
        </Space>
      </Card>
    </div>
  )
}

export default HomePage