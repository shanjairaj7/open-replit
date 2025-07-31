import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface Customer {
  id: string;
  name: string;
  email: string;
  status: 'active' | 'inactive';
  lastContact: string;
}

interface CustomerCardProps {
  customer: Customer;
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
}

export const CustomerCard: React.FC<CustomerCardProps> = ({ customer, onEdit, onDelete }) => {
  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-lg font-semibold">{customer.name}</CardTitle>
        <Badge variant={customer.status === 'active' ? 'default' : 'secondary'}>
          {customer.status}
        </Badge>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">{customer.email}</p>
          <p className="text-xs text-muted-foreground">Last contact: {customer.lastContact}</p>
          <div className="flex gap-2 pt-2">
            <Button size="sm" onClick={() => onEdit(customer.id)}>
              Edit
            </Button>
            <Button size="sm" variant="destructive" onClick={() => onDelete(customer.id)}>
              Delete
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default CustomerCard;