import React from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { PageLayout } from "@/components/page-layout";

/**
 * BOILERPLATE PROFILE PAGE - SHADCN UI VERSION
 * 
 * This demonstrates profile components using shadcn/ui.
 * All styling is handled by Tailwind CSS with beautiful design out of the box.
 */
export default function ProfilePage() {
  return (
    <PageLayout title="Profile">
      <div className="space-y-8 px-4 lg:px-6">
      {/* Page Header */}
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-foreground mb-4">
          User Profile
        </h1>
        <p className="text-lg text-muted-foreground">
          Manage your profile information and preferences with shadcn/ui components.
        </p>
      </div>

      {/* Profile Information Card */}
      <Card className="max-w-2xl mx-auto">
        <CardHeader>
          <CardTitle>Profile Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            <div className="flex items-start gap-6">
              {/* User Avatar */}
              <Avatar className="h-20 w-20">
                <AvatarImage src="https://github.com/shadcn.png" alt="@shadcn" />
                <AvatarFallback className="bg-blue-500 text-white text-2xl">JD</AvatarFallback>
              </Avatar>
              <div className="flex-1">
                <h3 className="text-2xl font-bold text-gray-900">
                  John Doe
                </h3>
                <p className="text-gray-600 mb-2">
                  john.doe@example.com
                </p>
                <div className="flex gap-2">
                  <Badge variant="secondary">
                    Premium User
                  </Badge>
                  <Badge variant="outline">
                    Verified
                  </Badge>
                </div>
              </div>
            </div>
            
            {/* Profile Stats */}
            <div className="grid grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">
                  24
                </div>
                <p className="text-sm text-gray-600">
                  Projects
                </p>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">
                  156
                </div>
                <p className="text-sm text-gray-600">
                  Tasks
                </p>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">
                  89%
                </div>
                <p className="text-sm text-gray-600">
                  Completed
                </p>
              </div>
            </div>
            
            {/* Action Buttons */}
            <div className="flex gap-4 pt-4">
              <Button size="lg">
                Edit Profile
              </Button>
              <Button variant="outline" size="lg">
                Change Password
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Additional Profile Sections */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-full" />
                <p className="text-sm">Completed project "Website Redesign"</p>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-500 rounded-full" />
                <p className="text-sm">Updated profile settings</p>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-purple-500 rounded-full" />
                <p className="text-sm">Joined team "Development"</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Button variant="ghost" className="w-full justify-start">
                📊 View Analytics
              </Button>
              <Button variant="ghost" className="w-full justify-start">
                ⚙️ Account Settings
              </Button>
              <Button variant="ghost" className="w-full justify-start">
                🔔 Notification Preferences
              </Button>
              <Button variant="ghost" className="w-full justify-start">
                🛡️ Privacy & Security
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
      </div>
    </PageLayout>
  );
}