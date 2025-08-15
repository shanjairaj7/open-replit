"""
Database Cost Analysis Framework
Analyze real costs for different database architectures at scale
"""

import json
from datetime import datetime

class DatabaseCostAnalyzer:
    """
    Analyze costs for different database approaches at various scales
    """
    
    def __init__(self):
        self.analysis_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
    def calculate_sqlite_costs(self):
        """SQLite cost analysis - file-based approach"""
        
        scenarios = {
            "small_scale": {
                "projects_per_month": 100,
                "avg_db_size_mb": 10,
                "description": "Small hobby projects, personal use"
            },
            "medium_scale": {
                "projects_per_month": 1000, 
                "avg_db_size_mb": 50,
                "description": "Growing platform, small teams"
            },
            "large_scale": {
                "projects_per_month": 10000,
                "avg_db_size_mb": 100,
                "description": "Popular platform, many users"
            }
        }
        
        costs = {}
        
        for scale_name, scenario in scenarios.items():
            projects = scenario["projects_per_month"]
            db_size_mb = scenario["avg_db_size_mb"]
            
            # Storage costs (assuming cloud storage)
            total_storage_gb = (projects * db_size_mb) / 1024
            storage_cost = total_storage_gb * 0.023  # AWS S3 pricing per GB
            
            # Backup costs
            backup_cost = total_storage_gb * 0.023 * 0.5  # 50% backup overhead
            
            # No database server costs
            server_cost = 0
            
            # Operational costs (minimal)
            operational_cost = 0
            
            total_monthly_cost = storage_cost + backup_cost + server_cost + operational_cost
            cost_per_project = total_monthly_cost / projects if projects > 0 else 0
            
            costs[scale_name] = {
                "scenario": scenario,
                "storage_cost": round(storage_cost, 2),
                "backup_cost": round(backup_cost, 2), 
                "server_cost": server_cost,
                "operational_cost": operational_cost,
                "total_monthly_cost": round(total_monthly_cost, 2),
                "cost_per_project": round(cost_per_project, 4),
                "advantages": [
                    "Zero infrastructure management",
                    "Perfect project isolation", 
                    "Easy backup/restore per project",
                    "No connection limits",
                    "Scales with usage only"
                ],
                "limitations": [
                    "No concurrent access across services",
                    "Limited for real-time applications",
                    "File system dependency"
                ]
            }
        
        return costs
    
    def calculate_postgresql_costs(self):
        """PostgreSQL cost analysis - shared database approach"""
        
        scenarios = {
            "small_scale": {
                "projects_per_month": 100,
                "concurrent_connections": 50,
                "db_instance": "t3.micro"
            },
            "medium_scale": {
                "projects_per_month": 1000,
                "concurrent_connections": 200, 
                "db_instance": "t3.small"
            },
            "large_scale": {
                "projects_per_month": 10000,
                "concurrent_connections": 1000,
                "db_instance": "t3.large"
            }
        }
        
        # AWS RDS pricing (approximate)
        instance_costs = {
            "t3.micro": 15,
            "t3.small": 30,
            "t3.medium": 60,
            "t3.large": 120,
            "t3.xlarge": 240
        }
        
        costs = {}
        
        for scale_name, scenario in scenarios.items():
            projects = scenario["projects_per_month"]
            instance = scenario["db_instance"]
            
            # Database server cost
            server_cost = instance_costs[instance]
            
            # Storage cost (20GB + growth)
            storage_gb = 20 + (projects * 0.1)  # 100MB per project
            storage_cost = storage_gb * 0.115  # RDS storage pricing
            
            # Backup costs
            backup_cost = storage_cost * 0.3  # 30% of storage
            
            # Monitoring and operational costs
            operational_cost = 10  # CloudWatch, maintenance
            
            total_monthly_cost = server_cost + storage_cost + backup_cost + operational_cost
            cost_per_project = total_monthly_cost / projects if projects > 0 else 0
            
            costs[scale_name] = {
                "scenario": scenario,
                "server_cost": server_cost,
                "storage_cost": round(storage_cost, 2),
                "backup_cost": round(backup_cost, 2),
                "operational_cost": operational_cost,
                "total_monthly_cost": round(total_monthly_cost, 2),
                "cost_per_project": round(cost_per_project, 4),
                "advantages": [
                    "Professional database features",
                    "ACID compliance",
                    "Concurrent access",
                    "Advanced querying",
                    "Schema isolation possible"
                ],
                "limitations": [
                    "Fixed server costs regardless of usage",
                    "Connection limits",
                    "More complex setup",
                    "Schema conflicts possible"
                ]
            }
        
        return costs
    
    def calculate_mongodb_costs(self):
        """MongoDB Atlas cost analysis"""
        
        scenarios = {
            "small_scale": {
                "projects_per_month": 100,
                "data_size_gb": 5,
                "tier": "M10"
            },
            "medium_scale": {
                "projects_per_month": 1000,
                "data_size_gb": 50,
                "tier": "M20"
            },
            "large_scale": {
                "projects_per_month": 10000,
                "data_size_gb": 500,
                "tier": "M40"
            }
        }
        
        # MongoDB Atlas pricing (approximate)
        atlas_costs = {
            "M0": 0,      # Free tier
            "M2": 9,      # Shared
            "M5": 15,     # Shared 
            "M10": 57,    # Dedicated
            "M20": 120,   # Dedicated
            "M30": 240,   # Dedicated
            "M40": 480    # Dedicated
        }
        
        costs = {}
        
        for scale_name, scenario in scenarios.items():
            projects = scenario["projects_per_month"]
            tier = scenario["tier"]
            data_size = scenario["data_size_gb"]
            
            # Base cluster cost
            cluster_cost = atlas_costs[tier]
            
            # Data transfer costs (minimal for most use cases)
            transfer_cost = 2
            
            # Storage overage (if any)
            included_storage = 10 if tier in ["M10", "M20"] else 20
            extra_storage = max(0, data_size - included_storage)
            storage_cost = extra_storage * 0.25  # Per GB overage
            
            # Backup (included in most tiers)
            backup_cost = 0
            
            total_monthly_cost = cluster_cost + transfer_cost + storage_cost + backup_cost
            cost_per_project = total_monthly_cost / projects if projects > 0 else 0
            
            costs[scale_name] = {
                "scenario": scenario,
                "cluster_cost": cluster_cost,
                "storage_cost": round(storage_cost, 2),
                "transfer_cost": transfer_cost,
                "backup_cost": backup_cost,
                "total_monthly_cost": round(total_monthly_cost, 2),
                "cost_per_project": round(cost_per_project, 4),
                "advantages": [
                    "Managed service",
                    "Flexible schemas",
                    "Built-in scaling",
                    "Document-based",
                    "Good for rapid development"
                ],
                "limitations": [
                    "Fixed costs regardless of usage",
                    "Learning curve for SQL developers",
                    "Less mature ecosystem",
                    "Vendor lock-in"
                ]
            }
        
        return costs
    
    def generate_cost_comparison(self):
        """Generate comprehensive cost comparison"""
        
        sqlite_costs = self.calculate_sqlite_costs()
        postgres_costs = self.calculate_postgresql_costs()
        mongodb_costs = self.calculate_mongodb_costs()
        
        comparison = {
            "analysis_metadata": {
                "timestamp": datetime.now().isoformat(),
                "purpose": "Database cost analysis for AI coder system",
                "assumptions": [
                    "AWS/Cloud hosting",
                    "Standard usage patterns",
                    "Monthly cost calculations",
                    "US East region pricing"
                ]
            },
            "cost_analysis": {
                "sqlite": sqlite_costs,
                "postgresql": postgres_costs,
                "mongodb": mongodb_costs
            },
            "summary_comparison": self._create_summary_table(sqlite_costs, postgres_costs, mongodb_costs),
            "recommendations": self._generate_recommendations(sqlite_costs, postgres_costs, mongodb_costs)
        }
        
        return comparison
    
    def _create_summary_table(self, sqlite_costs, postgres_costs, mongodb_costs):
        """Create summary comparison table"""
        
        summary = {}
        
        for scale in ["small_scale", "medium_scale", "large_scale"]:
            summary[scale] = {
                "sqlite": {
                    "total_cost": sqlite_costs[scale]["total_monthly_cost"],
                    "cost_per_project": sqlite_costs[scale]["cost_per_project"]
                },
                "postgresql": {
                    "total_cost": postgres_costs[scale]["total_monthly_cost"],
                    "cost_per_project": postgres_costs[scale]["cost_per_project"]
                },
                "mongodb": {
                    "total_cost": mongodb_costs[scale]["total_monthly_cost"],
                    "cost_per_project": mongodb_costs[scale]["cost_per_project"]
                }
            }
        
        return summary
    
    def _generate_recommendations(self, sqlite_costs, postgres_costs, mongodb_costs):
        """Generate recommendations based on cost analysis"""
        
        recommendations = {
            "cost_winner_by_scale": {
                "small_scale": "SQLite (${:.2f}/month)".format(sqlite_costs["small_scale"]["total_monthly_cost"]),
                "medium_scale": "SQLite (${:.2f}/month)".format(sqlite_costs["medium_scale"]["total_monthly_cost"]), 
                "large_scale": "SQLite (${:.2f}/month)".format(sqlite_costs["large_scale"]["total_monthly_cost"])
            },
            "break_even_analysis": {
                "sqlite_vs_postgres": "PostgreSQL never breaks even on cost alone",
                "sqlite_vs_mongodb": "MongoDB never breaks even for simple use cases",
                "cost_efficiency": "SQLite scales linearly with usage, others have fixed costs"
            },
            "decision_matrix": {
                "choose_sqlite_if": [
                    "Cost is primary concern",
                    "Projects are mostly independent",
                    "Simple to medium complexity",
                    "Good isolation requirements",
                    "Variable usage patterns"
                ],
                "choose_postgresql_if": [
                    "Need concurrent access",
                    "Complex queries and relationships",
                    "ACID compliance critical",
                    "Team familiar with SQL",
                    "Willing to pay for features"
                ],
                "choose_mongodb_if": [
                    "Document-based data model fits",
                    "Rapid development needed",
                    "Flexible schemas required",
                    "NoSQL expertise available",
                    "Willing to pay premium"
                ]
            },
            "hybrid_approach": {
                "description": "Start with SQLite, upgrade when needed",
                "implementation": "Use SQLAlchemy for database-agnostic code",
                "upgrade_triggers": [
                    "Concurrent access requirements",
                    "Complex query needs",
                    "Team growth beyond simple projects",
                    "Performance bottlenecks"
                ],
                "cost_benefit": "Pay only when features are actually needed"
            }
        }
        
        return recommendations
    
    def save_analysis(self):
        """Save complete cost analysis"""
        
        analysis = self.generate_cost_comparison()
        
        filename = f"database_cost_analysis_{self.analysis_timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        print(f"💰 Cost analysis saved: {filename}")
        
        # Print summary
        print("\n📊 COST ANALYSIS SUMMARY")
        print("=" * 50)
        
        summary = analysis["summary_comparison"]
        
        for scale in ["small_scale", "medium_scale", "large_scale"]:
            print(f"\n{scale.replace('_', ' ').title()}:")
            print(f"  SQLite:     ${summary[scale]['sqlite']['total_cost']}/month (${summary[scale]['sqlite']['cost_per_project']:.4f}/project)")
            print(f"  PostgreSQL: ${summary[scale]['postgresql']['total_cost']}/month (${summary[scale]['postgresql']['cost_per_project']:.4f}/project)")
            print(f"  MongoDB:    ${summary[scale]['mongodb']['total_cost']}/month (${summary[scale]['mongodb']['cost_per_project']:.4f}/project)")
        
        print(f"\n🏆 WINNER: SQLite at all scales")
        print(f"💡 HYBRID APPROACH: Start SQLite → Upgrade PostgreSQL when needed")
        
        return filename, analysis

def main():
    """Run cost analysis"""
    
    print("💰 Database Cost Analysis for AI Coder System")
    print("=" * 55)
    
    analyzer = DatabaseCostAnalyzer()
    filename, analysis = analyzer.save_analysis()
    
    print(f"\n🎯 KEY INSIGHTS:")
    recommendations = analysis["recommendations"]
    
    print(f"\n💵 Cost Winners:")
    for scale, winner in recommendations["cost_winner_by_scale"].items():
        print(f"  {scale}: {winner}")
    
    print(f"\n🔄 Recommended Approach:")
    hybrid = recommendations["hybrid_approach"]
    print(f"  Strategy: {hybrid['description']}")
    print(f"  Implementation: {hybrid['implementation']}")
    
    print(f"\n📈 When to upgrade:")
    for trigger in hybrid["upgrade_triggers"]:
        print(f"  - {trigger}")
    
    return analysis

if __name__ == "__main__":
    main()