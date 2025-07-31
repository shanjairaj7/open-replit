import React from 'react';
import { Badge } from '@/components/ui/badge';

interface Transaction {
  id: string;
  customer: string;
  amount: number;
  status: 'completed' | 'pending' | 'failed';
  date: string;
}

const transactions: Transaction[] = [
  { id: 'TXN001', customer: 'John Doe', amount: 250.00, status: 'completed', date: '2024-01-15' },
  { id: 'TXN002', customer: 'Jane Smith', amount: 175.50, status: 'pending', date: '2024-01-14' },
  { id: 'TXN003', customer: 'Bob Johnson', amount: 450.00, status: 'completed', date: '2024-01-14' },
  { id: 'TXN004', customer: 'Alice Brown', amount: 300.00, status: 'failed', date: '2024-01-13' },
  { id: 'TXN005', customer: 'Charlie Wilson', amount: 525.00, status: 'completed', date: '2024-01-12' },
];

const RecentTransactions: React.FC = () => {
  const getStatusBadge = (status: Transaction['status']) => {
    const variants = {
      completed: 'bg-green-100 text-green-800',
      pending: 'bg-yellow-100 text-yellow-800',
      failed: 'bg-red-100 text-red-800',
    };
    return variants[status];
  };

  return (
    <div className="space-y-4">
      {transactions.map((transaction) => (
        <div key={transaction.id} className="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition-colors">
          <div className="space-y-1">
            <p className="text-sm font-medium text-gray-900">{transaction.customer}</p>
            <p className="text-xs text-gray-500">{transaction.id} • {transaction.date}</p>
          </div>
          <div className="flex items-center space-x-3">
            <span className="text-sm font-semibold text-gray-900">
              ${transaction.amount.toFixed(2)}
            </span>
            <Badge className={getStatusBadge(transaction.status)}>
              {transaction.status}
            </Badge>
          </div>
        </div>
      ))}
    </div>
  );
};

export default RecentTransactions;