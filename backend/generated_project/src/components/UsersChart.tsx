import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const data = [
  { month: 'Jan', users: 400 },
  { month: 'Feb', users: 600 },
  { month: 'Mar', users: 800 },
  { month: 'Apr', users: 1000 },
  { month: 'May', users: 1200 },
  { month: 'Jun', users: 1600 },
];

const UsersChart: React.FC = () => {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
        <XAxis 
          dataKey="month" 
          tick={{ fontSize: 12 }}
          stroke="#666"
        />
        <YAxis 
          tick={{ fontSize: 12 }}
          stroke="#666"
        />
        <Tooltip 
          formatter={(value: number) => [value.toLocaleString(), 'Users']}
          labelStyle={{ color: '#333' }}
          contentStyle={{ 
            backgroundColor: '#fff', 
            border: '1px solid #e0e0e0',
            borderRadius: '6px'
          }}
        />
        <Area 
          type="monotone" 
          dataKey="users" 
          stroke="#3b82f6" 
          fill="#3b82f6" 
          fillOpacity={0.2}
          strokeWidth={3}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
};

export default UsersChart;