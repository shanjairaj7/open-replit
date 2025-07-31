import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Sparkles, Code2, Palette, Zap } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Welcome Back</h1>
          <p className="text-muted-foreground text-lg">
            Ready to build something amazing?
          </p>
        </div>
        <Avatar className="h-12 w-12">
          <AvatarImage src="/placeholder-avatar.jpg" />
          <AvatarFallback className="bg-gradient-to-br from-blue-500 to-purple-600 text-white">
            JD
          </AvatarFallback>
        </Avatar>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card className="relative overflow-hidden">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium">Modern Stack</CardTitle>
              <Code2 className="h-4 w-4 text-blue-500" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">React 18</div>
            <p className="text-xs text-muted-foreground">
              Latest React with TypeScript
            </p>
          </CardContent>
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent" />
        </Card>

        <Card className="relative overflow-hidden">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium">Beautiful UI</CardTitle>
              <Palette className="h-4 w-4 text-pink-500" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">shadcn/ui</div>
            <p className="text-xs text-muted-foreground">
              Premium components
            </p>
          </CardContent>
          <div className="absolute inset-0 bg-gradient-to-br from-pink-500/5 to-transparent" />
        </Card>

        <Card className="relative overflow-hidden">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium">Fast Build</CardTitle>
              <Zap className="h-4 w-4 text-yellow-500" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">Vite</div>
            <p className="text-xs text-muted-foreground">
              Lightning fast development
            </p>
          </CardContent>
          <div className="absolute inset-0 bg-gradient-to-br from-yellow-500/5 to-transparent" />
        </Card>

        <Card className="relative overflow-hidden">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium">Animations</CardTitle>
              <Sparkles className="h-4 w-4 text-purple-500" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">Motion</div>
            <p className="text-xs text-muted-foreground">
              Smooth transitions
            </p>
          </CardContent>
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent" />
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Quick Start Guide</CardTitle>
              <CardDescription>
                Everything is pre-configured and ready to use
              </CardDescription>
            </div>
            <Badge variant="secondary" className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100">
              Ready
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <h4 className="font-medium">🚀 Development Features</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Hot module replacement with Vite</li>
                <li>• TypeScript support out of the box</li>
                <li>• ESLint and Prettier configured</li>
                <li>• Path aliases (@/* imports)</li>
              </ul>
            </div>
            <div className="space-y-2">
              <h4 className="font-medium">🎨 UI Components</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Complete shadcn/ui component library</li>
                <li>• Dark/light mode support</li>
                <li>• Responsive design patterns</li>
                <li>• Accessible by default</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}