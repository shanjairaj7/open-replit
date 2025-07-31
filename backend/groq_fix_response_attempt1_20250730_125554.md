# Groq Fix Response - Attempt 1 - 2025-07-30 12:55:54

## Build Errors
src/App.tsx(1,56): error TS2307: Cannot find module 'react-router-dom' or its corresponding type declarations.
src/components/app-sidebar.tsx(26,35): error TS2307: Cannot find module 'react-router-dom' or its corresponding type declarations.
src/components/ui/accordion.tsx(2,37): error TS2307: Cannot find module '@radix-ui/react-accordion' or its corresponding type declarations.
src/components/ui/alert-dialog.tsx(4,39): error TS2307: Cannot find module '@radix-ui/react-alert-dialog' or its corresponding type declarations.
src/components/ui/aspect-ratio.tsx(1,39): error TS2307: Cannot find module '@radix-ui/react-aspect-ratio' or its corresponding type declarations.
src/components/ui/avatar.tsx(4,34): error TS2307: Cannot find module '@radix-ui/react-avatar' or its corresponding type declarations.
src/components/ui/badge.tsx(2,22): error TS2307: Cannot find module '@radix-ui/react-slot' or its corresponding type declarations.
src/components/ui/breadcrumb.tsx(2,22): error TS2307: Cannot find module '@radix-ui/react-slot' or its corresponding type declarations.
src/components/ui/breadcrumb.tsx(4,54): error TS2307: Cannot find module '@radix-ui/react-icons' or its corresponding type declarations.
src/components/ui/button.tsx(2,22): error TS2307: Cannot find module '@radix-ui/react-slot' or its corresponding type declarations.
src/components/ui/calendar.tsx(7,60): error TS2307: Cannot find module 'react-day-picker' or its corresponding type declarations.
src/components/ui/calendar.tsx(37,31): error TS7006: Parameter 'date' implicitly has an 'any' type.
src/components/ui/calendar.tsx(126,18): error TS7031: Binding element 'className' implicitly has an 'any' type.
src/components/ui/calendar.tsx(126,29): error TS7031: Binding element 'rootRef' implicitly has an 'any' type.
src/components/ui/calendar.tsx(136,21): error TS7031: Binding element 'className' implicitly has an 'any' type.
src/components/ui/calendar.tsx(136,32): error TS7031: Binding element 'orientation' implicitly has an 'any' type.
src/components/ui/calendar.tsx(157,24): error TS7031: Binding element 'children' implicitly has an 'any' type.
src/components/ui/carousel.tsx(6,8): error TS2307: Cannot find module 'embla-carousel-react' or its corresponding type declarations.
src/components/ui/carousel.tsx(9,47): error TS2307: Cannot find module '@radix-ui/react-icons' or its corresponding type declarations.
src/components/ui/chart.tsx(2,36): error TS2307: Cannot find module 'recharts' or its corresponding type declarations.
src/components/ui/chart.tsx(180,23): error TS7006: Parameter 'item' implicitly has an 'any' type.
src/components/ui/chart.tsx(180,29): error TS7006: Parameter 'index' implicitly has an 'any' type.
src/components/ui/chart.tsx(276,21): error TS7006: Parameter 'item' implicitly has an 'any' type.
src/components/ui/command.tsx(4,45): error TS2307: Cannot find module 'cmdk' or its corresponding type declarations.
src/components/ui/drawer.tsx(2,43): error TS2307: Cannot find module 'vaul' or its corresponding type declarations.
src/components/ui/form.tsx(3,22): error TS2307: Cannot find module '@radix-ui/react-slot' or its corresponding type declarations.
src/components/ui/form.tsx(12,8): error TS2307: Cannot find module 'react-hook-form' or its corresponding type declarations.
src/components/ui/hover-card.tsx(2,37): error TS2307: Cannot find module '@radix-ui/react-hover-card' or its corresponding type declarations.
src/components/ui/input-otp.tsx(4,43): error TS2307: Cannot find module 'input-otp' or its corresponding type declarations.
src/components/ui/input-otp.tsx(47,61): error TS2339: Property 'slots' does not exist on type '{}'.
src/components/ui/menubar.tsx(2,35): error TS2307: Cannot find module '@radix-ui/react-menubar' or its corresponding type declarations.
src/components/ui/navigation-menu.tsx(2,42): error TS2307: Cannot find module '@radix-ui/react-navigation-menu' or its corresponding type declarations.
src/components/ui/radio-group.tsx(4,38): error TS2307: Cannot find module '@radix-ui/react-radio-group' or its corresponding type declarations.
src/components/ui/select.tsx(2,34): error TS2307: Cannot find module '@radix-ui/react-select' or its corresponding type declarations.
src/components/ui/sidebar.tsx(4,22): error TS2307: Cannot find module '@radix-ui/react-slot' or its corresponding type declarations.
src/components/ui/slider.tsx(4,34): error TS2307: Cannot find module '@radix-ui/react-slider' or its corresponding type declarations.
src/components/ui/sonner.tsx(1,26): error TS2307: Cannot find module 'next-themes' or its corresponding type declarations.
src/components/ui/sonner.tsx(2,49): error TS2307: Cannot find module 'sonner' or its corresponding type declarations.
src/components/ui/toggle-group.tsx(4,39): error TS2307: Cannot find module '@radix-ui/react-toggle-group' or its corresponding type declarations.
src/components/ui/toggle.tsx(2,34): error TS2307: Cannot find module '@radix-ui/react-toggle' or its corresponding type declarations.
src/pages/Dashboard.tsx(6,109): error TS2307: Cannot find module 'recharts' or its corresponding type declarations.
src/pages/Dashboard.tsx(194,35): error TS7006: Parameter 'value' implicitly has an 'any' type.
src/pages/Inventory.tsx(9,90): error TS2307: Cannot find module 'recharts' or its corresponding type declarations.
src/pages/Inventory.tsx(219,20): error TS2322: Type '"warning"' is not assignable to type '"default" | "destructive" | "outline" | "secondary" | null | undefined'.
src/pages/Inventory.tsx(287,35): error TS7006: Parameter 'value' implicitly has an 'any' type.
src/pages/Inventory.tsx(360,30): error TS2322: Type '"default" | "destructive" | "secondary" | "warning"' is not assignable to type '"default" | "destructive" | "outline" | "secondary" | null | undefined'.
vite.config.ts(2,25): error TS2307: Cannot find module '@tailwindcss/vite' or its corresponding type declarations.

## Fix Response

<artifact type="text" title="Build Error Fixes">
The build errors indicate missing dependencies. I'll fix these by:

1. Installing the missing dependencies via npm
2. Fixing type issues in the components
3. Updating the Badge component to handle the 'warning' variant
4. Fixing implicit any types in the charts

The main issues are:
- Missing react-router-dom and recharts
- Missing Radix UI dependencies
- Missing recharts types
- Badge component doesn't support 'warning' variant
- Chart parameter types need explicit typing
</artifact>

<action type="file" filePath="package.json">
{
  "name": "demo_dashboard",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "preview": "vite preview"
  },
  "dependencies": {
    "@hookform/resolvers": "^3.9.1",
    "@radix-ui/react-accordion": "^1.2.2",
    "@radix-ui/react-alert-dialog": "^1.1.4",
    "@radix-ui/react-aspect-ratio": "^1.1.1",
    "@radix-ui/react-avatar": "^1.1.2",
    "@radix-ui/react-checkbox": "^1.1.3",
    "@radix-ui/react-collapsible": "^1.1.2",
    "@radix-ui/react-context-menu": "^2.2.4",
    "@radix-ui/react-dialog": "^1.1.4",
    "@radix-ui/react-dropdown-menu": "^2.1.4",
    "@radix-ui/react-hover-card": "^1.1.4",
    "@radix-ui/react-icons": "^1.3.2",
    "@radix-ui/react-label": "^2.1.1",
    "@radix-ui/react-menubar": "^1.1.4",
    "@radix-ui/react-navigation-menu": "^1.2.3",
    "@radix-ui/react-popover": "^1.1.4",
    "@radix-ui/react-progress": "^1.1.1",
    "@radix-ui/react-radio-group": "^1.2.2",
    "@radix-ui/react-scroll-area": "^1.2.2",
    "@radix-ui/react-select": "^2.1.4",
    "@radix-ui/react-separator": "^1.1.1",
    "@radix-ui/react-slider": "^1.2.2",
    "@radix-ui/react-slot": "^1.1.1",
    "@radix-ui/react-switch": "^1.1.2",
    "@radix-ui/react-tabs": "^1.1.2",
    "@radix-ui/react-toggle": "^1.1.1",
    "@radix-ui/react-toggle-group": "^1.1.1",
    "@radix-ui/react-tooltip": "^1.1.6",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "cmdk": "^1.0.4",
    "embla-carousel-react": "^8.5.1",
    "input-otp": "^1.4.1",
    "lucide-react": "^0.468.0",
    "next-themes": "^0.4.4",
    "react": "^18.3.1",
    "react-day-picker": "^8.10.1",
    "react-dom": "^18.3.1",
    "react-hook-form": "^7.54.0",
    "react-router-dom": "^7.0.2",
    "recharts": "^2.14.1",
    "sonner": "^1.7.1",
    "tailwind-merge": "^2.5.5",
    "tailwindcss-animate": "^1.0.7",
    "vaul": "^1.1.2",
    "zod": "^3.24.1"
  },
  "devDependencies": {
    "@eslint/js": "^9.15.0",
    "@tailwindcss/vite": "^4.0.0-beta.8",
    "@types/node": "^22.10.2",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.5",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "eslint": "^9.15.0",
    "eslint-plugin-react-hooks": "^5.0.0",
    "eslint-plugin-react-refresh": "^0.4.14",
    "globals": "^15.12.0",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.16",
    "typescript": "~5.6.2",
    "typescript-eslint": "^8.15.0",
    "vite": "^6.0.3"
  }
}
</action>

<action type="file" filePath="src/components/ui/badge.tsx">
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground",
        warning:
          "border-transparent bg-orange-500 text-white hover:bg-orange-500/80",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
</action>

<action type="file" filePath="src/pages/Dashboard.tsx">
import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { TrendingUp, TrendingDown, DollarSign, Package, ShoppingCart, Users } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'
import { Skeleton } from '@/components/ui/skeleton'

const revenueData = [
  { name: 'Jan', revenue: 45000, orders: 320 },
  { name: 'Feb', revenue: 52000, orders: 380 },
  { name: 'Mar', revenue: 48000, orders: 350 },
  { name: 'Apr', revenue: 61000, orders: 420 },
  { name: 'May', revenue: 55000, orders: 390 },
  { name: 'Jun', revenue: 67000, orders: 450 },
  { name: 'Jul', revenue: 71000, orders: 480 },
  { name: 'Aug', revenue: 59000, orders: 410 },
  { name: 'Sep', revenue: 78000, orders: 520 },
  { name: 'Oct', revenue: 82000, orders: 550 },
  { name: 'Nov', revenue: 91000, orders: 610 },
  { name: 'Dec', revenue: 88000, orders: 590 },
]

const topProducts = [
  { name: 'Wireless Headphones', sales: 1234, revenue: 98720 },
  { name: 'Smart Watch Pro', sales: 856, revenue: 171200 },
  { name: 'Laptop Stand', sales: 2341, revenue: 70230 },
  { name: 'Mechanical Keyboard', sales: 567, revenue: 45360 },
]

export default function Dashboard() {
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 1000)
    return () => clearTimeout(timer)
  }, [])

  const stats = [
    {
      title: 'Total Revenue',
      value: '$743,000',
      change: '+12.5%',
      trend: 'up',
      icon: DollarSign,
      color: 'text-green-600',
      bgColor: 'bg-green-100 dark:bg-green-900/20',
    },
    {
      title: 'Orders',
      value: '4,320',
      change: '+8.2%',
      trend: 'up',
      icon: ShoppingCart,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100 dark:bg-blue-900/20',
    },
    {
      title: 'Products',
      value: '1,234',
      change: '+23',
      trend: 'up',
      icon: Package,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100 dark:bg-purple-900/20',
    },
    {
      title: 'Customers',
      value: '8,549',
      change: '-2.4%',
      trend: 'down',
      icon: Users,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100 dark:bg-orange-900/20',
    },
  ]

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="border-border/50">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <Skeleton className="h-4 w-[100px]" />
                <Skeleton className="h-4 w-4" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-[120px] mb-1" />
                <Skeleton className="h-3 w-[80px]" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
          <Card className="col-span-4 border-border/50">
            <CardHeader>
              <Skeleton className="h-4 w-[120px]" />
              <Skeleton className="h-3 w-[200px]" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-[300px] w-full" />
            </CardContent>
          </Card>
          <Card className="col-span-3 border-border/50">
            <CardHeader>
              <Skeleton className="h-4 w-[100px]" />
              <Skeleton className="h-3 w-[150px]" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-[300px] w-full" />
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-gray-900 to-gray-600 dark:from-gray-100 dark:to-gray-400 bg-clip-text text-transparent">
          Dashboard Overview
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Monitor your store's performance and key metrics
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, index) => (
          <Card
            key={index}
            className="border-border/50 bg-gradient-to-br from-white/50 to-white/30 dark:from-gray-900/50 dark:to-gray-800/50 backdrop-blur-sm transition-all duration-300 hover:shadow-lg hover:shadow-gray-200/50 dark:hover:shadow-gray-800/50 hover:-translate-y-0.5"
          >
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.title}
              </CardTitle>
              <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                <stat.icon className={`h-4 w-4 ${stat.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <div className="flex items-center gap-1 mt-1">
                {stat.trend === 'up' ? (
                  <TrendingUp className="h-3 w-3 text-green-600" />
                ) : (
                  <TrendingDown className="h-3 w-3 text-red-600" />
                )}
                <span
                  className={`text-xs font-medium ${
                    stat.trend === 'up' ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {stat.change}
                </span>
                <span className="text-xs text-muted-foreground">vs last month</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4 border-border/50 bg-gradient-to-br from-white/50 to-white/30 dark:from-gray-900/50 dark:to-gray-800/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-lg font-semibold">Revenue Overview</CardTitle>
            <p className="text-sm text-muted-foreground">Monthly revenue trends</p>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={revenueData}>
                <defs>
                  <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.1)" />
                <XAxis
                  dataKey="name"
                  stroke="rgba(148, 163, 184, 0.5)"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke="rgba(148, 163, 184, 0.5)"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value: number) => `$${value / 1000}k`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#fff',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="revenue"
                  stroke="#3b82f6"
                  fillOpacity={1}
                  fill="url(#colorRevenue)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="col-span-3 border-border/50 bg-gradient-to-br from-white/50 to-white/30 dark:from-gray-900/50 dark:to-gray-800/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-lg font-semibold">Top Products</CardTitle>
            <p className="text-sm text-muted-foreground">Best selling items</p>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {topProducts.map((product, index) => (
                <div key={index} className="flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-sm font-medium leading-none">{product.name}</p>
                    <p className="text-xs text-muted-foreground">{product.sales} sales</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">${product.revenue.toLocaleString()}</p>
                    <Badge variant="secondary" className="text-xs">
                      Top {index + 1}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
</action>

<action type="file" filePath="src/pages/Inventory.tsx">
import { useState, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { AlertCircle, Package, TrendingDown, Plus, Minus } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface InventoryItem {
  id: string
  name: string
  category: string
  currentStock: number
  minStock: number
  maxStock: number
  lastRestocked: string
  supplier: string
  unitPrice: number
  totalValue: number
  status: 'in_stock' | 'low_stock' | 'out_of_stock' | 'overstock'
}

const mockInventory: InventoryItem[] = [
  {
    id: '1',
    name: 'Wireless Headphones Pro',
    category: 'Electronics',
    currentStock: 45,
    minStock: 20,
    maxStock: 100,
    lastRestocked: '2024-01-15',
    supplier: 'TechSupply Co.',
    unitPrice: 299.99,
    totalValue: 13499.55,
    status: 'in_stock',
  },
  {
    id: '2',
    name: 'Smart Watch Series 8',
    category: 'Wearables',
    currentStock: 8,
    minStock: 15,
    maxStock: 50,
    lastRestocked: '2024-01-10',
    supplier: 'WearTech Ltd.',
    unitPrice: 449.99,
    totalValue: 3599.92,
    status: 'low_stock',
  },
  {
    id: '3',
    name: 'Ergonomic Office Chair',
    category: 'Furniture',
    currentStock: 0,
    minStock: 10,
    maxStock: 30,
    lastRestocked: '2023-12-20',
    supplier: 'ComfortPlus Inc.',
    unitPrice: 599.99,
    totalValue: 0,
    status: 'out_of_stock',
  },
  {
    id: '4',
    name: 'Mechanical Gaming Keyboard',
    category: 'Electronics',
    currentStock: 78,
    minStock: 25,
    maxStock: 80,
    lastRestocked: '2024-01-12',
    supplier: 'GameGear Pro',
    unitPrice: 159.99,
    totalValue: 12479.22,
    status: 'in_stock',
  },
  {
    id: '5',
    name: 'Yoga Mat Premium',
    category: 'Sports',
    currentStock: 234,
    minStock: 50,
    maxStock: 200,
    lastRestocked: '2024-01-08',
    supplier: 'FitLife Supplies',
    unitPrice: 49.99,
    totalValue: 11697.66,
    status: 'overstock',
  },
]

const stockAlerts = [
  {
    id: '1',
    type: 'low_stock',
    message: 'Smart Watch Series 8 is running low (8 units left)',
    severity: 'warning',
  },
  {
    id: '2',
    type: 'out_of_stock',
    message: 'Ergonomic Office Chair is out of stock',
    severity: 'critical',
  },
  {
    id: '3',
    type: 'overstock',
    message: 'Yoga Mat Premium is overstocked (234 units)',
    severity: 'info',
  },
]

export default function Inventory() {
  const [inventory] = useState<InventoryItem[]>(mockInventory)

  const inventoryStats = useMemo(() => {
    const totalValue = inventory.reduce((sum, item) => sum + item.totalValue, 0)
    const lowStockCount = inventory.filter(item => item.status === 'low_stock').length
    const outOfStockCount = inventory.filter(item => item.status === 'out_of_stock').length
    const inStockCount = inventory.filter(item => item.status === 'in_stock').length

    return {
      totalValue,
      lowStockCount,
      outOfStockCount,
      inStockCount,
    }
  }, [inventory])

  const categoryData = useMemo(() => {
    const data = inventory.reduce((acc, item) => {
      const existing = acc.find((d: { category: string }) => d.category === item.category)
      if (existing) {
        existing.value += item.totalValue
      } else {
        acc.push({ category: item.category, value: item.totalValue })
      }
      return acc
    }, [] as { category: string; value: number }[])

    return data.sort((a, b) => b.value - a.value)
  }, [inventory])

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'in_stock':
        return 'default'
      case 'low_stock':
        return 'warning'
      case 'out_of_stock':
        return 'destructive'
      case 'overstock':
        return 'secondary'
      default:
        return 'secondary'
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'in_stock':
        return 'In Stock'
      case 'low_stock':
        return 'Low Stock'
      case 'out_of_stock':
        return 'Out of Stock'
      case 'overstock':
        return 'Overstock'
      default:
        return status
    }
  }

  const getStockLevel = (current: number, min: number, max: number) => {
    const percentage = (current / max) * 100
    if (current === 0) return 0
    if (current <= min) return Math.max(percentage, 10)
    return Math.min(percentage, 100)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-gray-900 to-gray-600 dark:from-gray-100 dark:to-gray-400 bg-clip-text text-transparent">
          Inventory Management
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Track and manage your inventory levels
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="border-border/50 bg-gradient-to-br from-white/50 to-white/30 dark:from-gray-900/50 dark:to-gray-800/50 backdrop-blur-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Inventory Value</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${inventoryStats.totalValue.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Across all products</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-gradient-to-br from-white/50 to-white/30 dark:from-gray-900/50 dark:to-gray-800/50 backdrop-blur-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Stock</CardTitle>
            <Badge variant="default">{inventoryStats.inStockCount}</Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{inventoryStats.inStockCount}</div>
            <p className="text-xs text-muted-foreground">Products available</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-gradient-to-br from-white/50 to-white/30 dark:from-gray-900/50 dark:to-gray-800/50 backdrop-blur-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Low Stock</CardTitle>
            <Badge variant="warning">{inventoryStats.lowStockCount}</Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{inventoryStats.lowStockCount}</div>
            <p className="text-xs text-muted-foreground">Needs attention</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-gradient-to-br from-white/50 to-white/30 dark:from-gray-900/50 dark:to-gray-800/50 backdrop-blur-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Out of Stock</CardTitle>
            <Badge variant="destructive">{inventoryStats.outOfStockCount}</Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{inventoryStats.outOfStockCount}</div>
            <p className="text-xs text-muted-foreground">Urgent restock needed</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="border-border/50 bg-gradient-to-br from-white/50 to-white/30 dark:from-gray-900/50 dark:to-gray-800/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-lg font-semibold">Stock Alerts</CardTitle>
            <p className="text-sm text-muted-foreground">Items requiring attention</p>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {stockAlerts.map((alert) => (
                <Alert
                  key={alert.id}
                  variant={alert.severity === 'critical' ? 'destructive' : 'default'}
                  className="border-l-4"
                >
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>
                    {alert.type === 'low_stock' && 'Low Stock Alert'}
                    {alert.type === 'out_of_stock' && 'Out of Stock'}
                    {alert.type === 'overstock' && 'Overstock Notice'}
                  </AlertTitle>
                  <AlertDescription>{alert.message}</AlertDescription>
                </Alert>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-gradient-to-br from-white/50 to-white/30 dark:from-gray-900/50 dark:to-gray-800/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-lg font-semibold">Inventory by Category</CardTitle>
            <p className="text-sm text-muted-foreground">Value distribution</p>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={categoryData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.1)" />
                <XAxis
                  dataKey="category"
                  stroke="rgba(148, 163, 184, 0.5)"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke="rgba(148, 163, 184, 0.5)"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value: number) => `$${value / 1000}k`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#fff',
                  }}
                />
                <Bar dataKey="value" fill="#3b82f6" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/50 bg-gradient-to-br from-white/50 to-white/30 dark:from-gray-900/50 dark:to-gray-800/50 backdrop-blur-sm">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg font-semibold">Inventory Details</CardTitle>
              <p className="text-sm text-muted-foreground">Manage stock levels</p>
            </div>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Stock
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Product</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Current Stock</TableHead>
                  <TableHead>Min/Max</TableHead>
                  <TableHead>Stock Level</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Restocked</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {inventory.map((item) => (
                  <TableRow
                    key={item.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                  >
                    <TableCell className="font-medium">{item.name}</TableCell>
                    <TableCell>{item.category}</TableCell>
                    <TableCell>
                      <span className={`font-medium ${item.currentStock === 0 ? 'text-red-600' : ''}`}>
                        {item.currentStock}
                      </span>
                    </TableCell>
                    <TableCell>
                      {item.minStock} / {item.maxStock}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress
                          value={getStockLevel(item.currentStock, item.minStock, item.maxStock)}
                          className="h-2 w-20"
                        />
                        <span className="text-xs text-muted-foreground">
                          {Math.round(getStockLevel(item.currentStock, item.minStock, item.maxStock))}%
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={getStatusBadgeVariant(item.status) as any}>
                        {getStatusLabel(item.status)}
                      </Badge>
                    </TableCell>
                    <TableCell>{new Date(item.lastRestocked).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button variant="ghost" size="sm">
                          <Plus className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm">
                          <Minus className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
</action>

<action type="file" filePath="vite.config.ts">
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
</action>

<artifact type="text" title="Installation Instructions">
To fix all build errors, run the following commands:

```bash
npm install
```

This will install all the missing dependencies including:
- react-router-dom
- recharts
- All Radix UI components
- Tailwind CSS
- And other required packages

After installation, the build should work correctly.
</artifact>