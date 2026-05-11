package com.howardvox.ai;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;

public class VoxPipelineForegroundService extends Service {
    private static final String CHANNEL_ID = "vox_pipeline_processing";
    private static final int NOTIFICATION_ID = 4107;
    private static final String ACTION_START_OR_UPDATE = "com.howardvox.ai.action.PIPELINE_START_OR_UPDATE";
    private static final String ACTION_STOP = "com.howardvox.ai.action.PIPELINE_STOP";

    static void startOrUpdate(Context context, String jobId, int percent, String stage, String message) {
        Intent intent = new Intent(context, VoxPipelineForegroundService.class);
        intent.setAction(ACTION_START_OR_UPDATE);
        intent.putExtra("jobId", jobId);
        intent.putExtra("percent", Math.max(0, Math.min(100, percent)));
        intent.putExtra("stage", stage == null ? "processing" : stage);
        intent.putExtra("message", message == null || message.isEmpty() ? "Howard VOX is processing your song." : message);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(intent);
        } else {
            context.startService(intent);
        }
    }

    static void stop(Context context) {
        context.stopService(new Intent(context, VoxPipelineForegroundService.class));
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        ensureChannel();

        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                stopForeground(STOP_FOREGROUND_REMOVE);
            } else {
                stopForeground(true);
            }
            stopSelf();
            return START_NOT_STICKY;
        }

        int percent = intent == null ? 0 : intent.getIntExtra("percent", 0);
        String stage = intent == null ? "processing" : intent.getStringExtra("stage");
        String message = intent == null ? "Howard VOX is processing your song." : intent.getStringExtra("message");
        String jobId = intent == null ? "" : intent.getStringExtra("jobId");
        startForeground(NOTIFICATION_ID, buildNotification(jobId, percent, stage, message));
        return START_STICKY;
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE);
        } else {
            stopForeground(true);
        }
        super.onDestroy();
    }

    private void ensureChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return;
        }

        NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null || manager.getNotificationChannel(CHANNEL_ID) != null) {
            return;
        }

        NotificationChannel channel = new NotificationChannel(
            CHANNEL_ID,
            "Howard VOX processing",
            NotificationManager.IMPORTANCE_LOW
        );
        channel.setDescription("Shows progress while Howard VOX separates and analyzes audio.");
        manager.createNotificationChannel(channel);
    }

    private Notification buildNotification(String jobId, int percent, String stage, String message) {
        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
            ? new Notification.Builder(this, CHANNEL_ID)
            : new Notification.Builder(this);

        String cleanStage = stage == null || stage.isEmpty() ? "processing" : stage;
        String cleanMessage = message == null || message.isEmpty() ? "Howard VOX is processing your song." : message;
        builder
            .setSmallIcon(android.R.drawable.stat_sys_upload)
            .setContentTitle("Howard VOX is processing")
            .setContentText(cleanMessage)
            .setStyle(new Notification.BigTextStyle().bigText(cleanMessage + (jobId == null || jobId.isEmpty() ? "" : "\nJob: " + jobId)))
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setProgress(100, Math.max(0, Math.min(100, percent)), false)
            .setSubText(cleanStage);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            builder.setCategory(Notification.CATEGORY_PROGRESS);
        }

        return builder.build();
    }
}
