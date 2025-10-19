import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { CheckCircle } from "lucide-react";

interface ReactivateSubscriptionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  loading: boolean;
}

const ReactivateSubscriptionDialog: React.FC<ReactivateSubscriptionDialogProps> = ({
  open,
  onOpenChange,
  onConfirm,
  loading
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-500" />
            Reactivate Subscription
          </DialogTitle>
          <div className="pt-2">
            <div className="mb-2">
              Are you sure you want to reactivate your Elite Pack subscription?
            </div>
            <div className="bg-green-500/10 border border-green-500/20 rounded-md p-3 text-sm">
              <div className="flex items-start gap-2">
                <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />
                <div>
                  <div className="font-medium text-green-400">Good news!</div>
                  <div className="text-muted-foreground">
                    Your subscription will be reactivated immediately and will continue to renew at the end of your billing period.
                    All Elite features will remain available without interruption.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </DialogHeader>
        <DialogFooter className="flex flex-row justify-end gap-2 sm:justify-end">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            variant="default"
            onClick={onConfirm}
            disabled={loading}
            className="bg-green-600 hover:bg-green-700"
          >
            {loading ? "Reactivating..." : "Yes, Reactivate Subscription"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ReactivateSubscriptionDialog; 