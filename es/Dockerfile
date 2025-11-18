# Elasticsearch with Nori (Korean) analyzer plugin
FROM docker.elastic.co/elasticsearch/elasticsearch:9.2.0

COPY ./jvm.options.d /usr/share/elasticsearch/config/jvm.options.d
COPY ./synonyms /usr/share/elasticsearch/config/synonyms

RUN bin/elasticsearch-plugin install analysis-nori --batch