from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

print("="*80)
print("Neo4j 확인")
print("="*80)

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=("neo4j", NEO4J_PASSWORD))

    with driver.session() as session:
        # 노드 개수 확인
        result = session.run("MATCH (n) RETURN count(n) as node_count")
        node_count = result.single()["node_count"]
        print(f"\n총 노드 개수: {node_count}")

        # 관계 개수 확인
        result = session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
        rel_count = result.single()["rel_count"]
        print(f"총 관계 개수: {rel_count}")

        # 노드 레이블별 개수
        result = session.run("MATCH (n) RETURN labels(n) as label, count(n) as count")
        print("\n노드 레이블별 개수:")
        for record in result:
            print(f"  - {record['label']}: {record['count']}")

        # 관계 타입별 개수
        result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
        print("\n관계 타입별 개수:")
        for record in result:
            print(f"  - {record['type']}: {record['count']}")

    driver.close()

except Exception as e:
    print(f"❌ Neo4j 연결 실패: {e}")

print("\n" + "="*80)