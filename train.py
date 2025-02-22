from transformers import (
    AutoTokenizer,
    AutoConfig,
    LlamaForCausalLM,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)
from datasets import load_dataset
from huggingface_hub import login
import wandb
from utils import *


def train_model():
    # Set up login
    hf_token = "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"
    wb_token = "47230178200ca2166ee4759910652934320a9842"
    wandb.login(key=wb_token)
    login(token=hf_token)

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-hf")
    tokenized_data = load_dataset("xz56/openwebtext-tokenized-small")
    if tokenizer.pad_token is None:
        tokenizer.add_special_tokens({'pad_token': '[PAD]'})
    # Model configuration
    context_length = 2048
    config = AutoConfig.from_pretrained(
        "meta-llama/Llama-2-7b-hf",
        vocab_size=len(tokenizer),
        n_ctx=context_length,
        bos_token_id=tokenizer.bos_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )
    print('tokens', len(tokenizer))

    dim = 1536
    n_heads = 24
    n_layers = 24
    intermediate_size = 4096
    config.hidden_size = dim
    config.max_position_embeddings = dim
    config.num_attention_heads = n_heads
    config.num_hidden_layers = n_layers
    config.num_key_value_heads = n_heads
    config.intermediate_size = intermediate_size

    # Create and convert model to bitnet
    model = LlamaForCausalLM(config)
    print('llama_model', model)
    convert_to_bitnet(model, copy_weights=False)
    print('bitnet_model', model)

    # Set up DataCollator
    data_collator = DataCollatorForLanguageModeling(tokenizer, mlm=False)

    # Training arguments
    output_path = "/nfs/james/EML/LLaMA-BitNet/model"
    args = TrainingArguments(
        output_dir=output_path,
        per_device_train_batch_size=4,  # Reduced batch size
        per_device_eval_batch_size=4,  # Reduced batch size
        evaluation_strategy="steps",
        eval_steps=0.05,
        logging_steps=100,
        gradient_accumulation_steps=4,  # Increased accumulation steps
        num_train_epochs=1,
        weight_decay=0.01,
        warmup_steps=1000,  # Increased warmup steps
        lr_scheduler_type="cosine",
        learning_rate=1e-4,  # Adjusted learning rate
        save_steps=1000,  # Adjusted save steps
        fp16=True,
        report_to="wandb",
    )

    # Trainer initialization
    trainer = Trainer(
        model=model,
        tokenizer=tokenizer,
        args=args,
        data_collator=data_collator,
        train_dataset=tokenized_data["train"],
        eval_dataset=tokenized_data["test"],
    )

    # Start training
    trainer.train()

    # Save final model
    trainer.save_model(f"{output_path}/final_model")


train_model()
