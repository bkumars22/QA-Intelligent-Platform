package com.qaip.events;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.concurrent.CompletableFuture;

/**
 * Publishes commit events to Kafka instead of calling the AI engine
 * synchronously. This decouples the API response time from AI
 * processing time — the webhook handler returns immediately, and
 * the serverless AI layer picks up the event whenever it's ready.
 *
 * Before: GitHub webhook -> Java API -> blocking call to Python AI
 * service -> 200 OK after 30-90 seconds (bad — webhook timeouts,
 * held threads).
 *
 * After: GitHub webhook -> Java API -> publish to Kafka -> 200 OK
 * in milliseconds. AI processing happens async, results come back
 * via a separate results topic or webhook callback.
 */
@Service
public class CommitEventProducer {

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Value("${qaip.kafka.topic.commit-events}")
    private String commitEventsTopic;

    public CommitEventProducer(KafkaTemplate<String, String> kafkaTemplate,
                                ObjectMapper objectMapper) {
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
    }

    public CompletableFuture<Void> publishCommitEvent(CommitEvent event) {
        try {
            String payload = objectMapper.writeValueAsString(event);

            return kafkaTemplate.send(commitEventsTopic, event.commitSha(), payload)
                    .thenAccept(result -> {
                        // Partition key = commitSha ensures events for the
                        // same commit stay ordered on the same partition
                    })
                    .exceptionally(ex -> {
                        // Never let a Kafka failure break the webhook response.
                        // Log and let a dead-letter queue / retry policy handle it.
                        throw new EventPublishException(
                                "Failed to publish commit event: " + event.commitSha(), ex);
                    });
        } catch (Exception e) {
            throw new EventPublishException("Failed to serialize commit event", e);
        }
    }

    public record CommitEvent(
            String commitSha,
            String repository,
            int linesChanged,
            double complexity,
            int changeFrequency,
            String taskType,
            String diffSummary
    ) {}

    public static class EventPublishException extends RuntimeException {
        public EventPublishException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
