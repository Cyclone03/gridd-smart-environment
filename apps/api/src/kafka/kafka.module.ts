import { forwardRef, Module } from '@nestjs/common';
import { ObservationsModule } from '../observations/observations.module';
import { KAFKA_CONSUMER_FACTORY, kafkaConsumerFactory } from './kafka.consumer.factory';
import { KafkaConsumerService } from './kafka.consumer.service';
import { KAFKA_PRODUCER_FACTORY, kafkaProducerFactory } from './kafka.producer.factory';
import { KafkaProducerService } from './kafka.producer.service';

@Module({
  imports: [forwardRef(() => ObservationsModule)],
  providers: [
    KafkaConsumerService,
    { provide: KAFKA_CONSUMER_FACTORY, useValue: kafkaConsumerFactory },
    KafkaProducerService,
    { provide: KAFKA_PRODUCER_FACTORY, useValue: kafkaProducerFactory },
  ],
  exports: [KafkaConsumerService, KafkaProducerService],
})
export class KafkaModule {}
