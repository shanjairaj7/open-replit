import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const data = [
  { day: '1', sales: 120 },
  { day: '5', sales: 180 },
  { day: '10', sales: 200 },
  { day: '15', sales: 160 },
  { day: '20', sales: 220 },
  { day: '25', sales: 280 },
  { day: '30', sales: 240 },
];

const SalesChart: React.FC = () => {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
        <XAxis 
          dataKey="day" 
          tick={{ fontSize: 12 }}
          stroke="#666"
          label={{ value: 'Day of Month', position: 'insideBottom', offset: -5 }}
        />
        <YAxis 
          tick={{ fontSize: 12 }}
          stroke="#666"
        />
        <Tooltip 
          formatter={(value: number) => [value, 'Sales']}
          labelStyle={{ color: '#333' }}
          contentStyle={{ 
            backgroundColor: '#fff', 
            border: '1px solid #e0e0e0',
            borderRadius: '6px'
          }}
        />
        <Bar 
          dataKey="sales" 
          fill="#8b5cf6" 
          radius={[4, 4, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
};

export default SalesChart;